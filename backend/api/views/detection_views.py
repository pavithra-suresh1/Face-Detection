import logging
import os
import time
import uuid
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import UploadedImage, DetectedFace, RecognitionLog, KnownFace
from api.serializers import DetectedFaceSerializer
from api.services import RetinaFaceService, FaceRecognitionService, OpenCVService
from api.services.recognition_service import RecognitionService
from api.services.embedding_cache import EmbeddingCache
from api.config.thresholds import Thresholds
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from api.services.face_tracker import FaceTracker
from api.utils.preprocessing import ImagePreprocessor
from api.utils.preprocessing import ImageQualityValidator
from api.utils.preprocessing import FaceValidator

logger = logging.getLogger(__name__)


def _crop_and_save_face(image_path, region, padding=0.3, image=None):
    if image is None:
        image = cv2.imread(image_path)
    if image is None:
        return None
    h_img, w_img = image.shape[:2]
    x, y, w, h = int(region["x"]), int(region["y"]), int(region["w"]), int(region["h"])
    pad_x, pad_y = int(w * padding), int(h * padding)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w_img, x + w + pad_x)
    y2 = min(h_img, y + h + pad_y)
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_faces")
    os.makedirs(temp_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(temp_dir, filename)
    cv2.imwrite(path, crop)
    return path


@api_view(["POST"])
def detect_faces(request):
    image_id = request.data.get("image_id")
    recognize = request.data.get("recognize", True)
    if not image_id:
        return Response({"success": False, "message": "image_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        image = UploadedImage.objects.get(id=image_id, user=request.user)
    except UploadedImage.DoesNotExist:
        return Response({"success": False, "message": "Image not found."}, status=status.HTTP_404_NOT_FOUND)
    if not os.path.exists(image.image.path):
        return Response({"success": False, "message": "Image file not found on disk."}, status=status.HTTP_404_NOT_FOUND)
    img_bgr = cv2.imread(image.image.path)
    quality = ImageQualityValidator.validate_with_image(img_bgr)
    logger.debug("Quality check for image %s: valid=%s, issues=%d", image_id, quality["valid"], len(quality["issues"]))
    try:
        import tempfile
        fd, temp_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        if img_bgr is not None:
            img = ImagePreprocessor.auto_resize_numpy(img_bgr)
            cv2.imwrite(temp_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            detected = RetinaFaceService.detect_faces(temp_path)
        else:
            detected = RetinaFaceService.detect_faces(image.image.path)
        try:
            os.remove(temp_path)
        except Exception:
            pass
    except Exception as e:
        return Response({"success": False, "message": f"Face detection failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not detected:
        logger.info("No faces detected in image %s", image_id)
        return Response({"success": True, "message": "No faces detected.", "faces": [], "face_count": 0})
    logger.info("Detected %d face(s) in image %s", len(detected), image_id)
    face_validation = FaceValidator.validate_faces(detected)
    faces_data = []
    temp_paths = []
    for face_info in detected:
        crop_path = _crop_and_save_face(image.image.path, face_info["region"], image=img_bgr)
        if crop_path:
            temp_paths.append(crop_path)
        analysis_path = crop_path or image.image.path
        detected_face = DetectedFace.objects.create(
            image=image, bounding_box=face_info["region"], face_confidence=face_info["confidence"],
        )
        faces_data.append(DetectedFaceSerializer(detected_face).data)
    if recognize and face_validation["valid"] and face_validation["selected_face"]:
        selected = face_validation["selected_face"]
        selected_region = selected["region"]
        crop_path = _crop_and_save_face(image.image.path, selected_region, image=img_bgr)
        analysis_path = crop_path or image.image.path
        target_face = None
        for face_info in detected:
            if face_info["region"] == selected_region and face_info["confidence"] == selected["confidence"]:
                break
        for fd in faces_data:
            if fd["bounding_box"] == selected_region:
                target_face = fd
                break
        if target_face:
            try:
                embedding = FaceRecognitionService.get_embedding(analysis_path)
                if embedding:
                    detected_face_obj = DetectedFace.objects.get(id=target_face["id"])
                    detected_face_obj.embedding = embedding
                    detected_face_obj.save(update_fields=["embedding"])
                    match, distance, confidence = RecognitionService.recognize_face(embedding)
                    logger.info("Recognition for image %s: match=%s, distance=%.4f, confidence=%.2f",
                                image_id, match.name if match else None, distance, confidence)
                    RecognitionLog.objects.create(
                        detected_face=detected_face_obj, matched_face=match,
                        confidence=confidence, is_known=match is not None,
                    )
            except Exception as e:
                logger.exception("Recognition failed for image %s", image_id)
            if crop_path and os.path.exists(crop_path):
                try: os.remove(crop_path)
                except: pass
    for path in temp_paths:
        try: os.remove(path)
        except: pass
    for face in faces_data:
        log = RecognitionLog.objects.filter(detected_face_id=face["id"]).first()
        if log:
            face["is_known"] = log.is_known
            face["label"] = log.matched_face.name if log.matched_face else "Unknown"
            face["confidence"] = log.confidence
        else:
            face["is_known"] = None
            face["label"] = "Face detected"
    draw_data = [
        {"bounding_box": f["bounding_box"],
         "is_known": f.get("is_known"), "label": f.get("label"), "confidence": f.get("confidence")}
        for f in faces_data
    ]
    try:
        processed_rel_path = OpenCVService.draw_face_boxes(image.image.path, draw_data)
        image.processed_image = processed_rel_path
        image.save(update_fields=["processed_image"])
        processed_url = f"{settings.MEDIA_URL}{processed_rel_path}"
    except Exception:
        processed_url = None
    return Response({
        "success": True, "face_count": len(faces_data), "faces": faces_data,
        "processed_image": processed_url,
        "quality_warnings": quality["issues"],
        "face_validation": {
            "valid": face_validation["valid"],
            "issues": face_validation["issues"],
        },
    })


_face_tracker = FaceTracker(
    iou_threshold=Thresholds.TRACK_MATCH_SCORE,
    smoothing=Thresholds.TRACK_SMOOTHING,
    expire_seconds=Thresholds.TRACK_EXPIRE_SECONDS,
)
_last_labels = {}
_known_label_history = []
_recognition_retries = {}
_recognition_frame_counter = 0

try:
    _RECOGNITION_INTERVAL = Thresholds.RECOGNITION_FRAME_INTERVAL
except Exception:
    _RECOGNITION_INTERVAL = 3

try:
    _RECOGNITION_CACHE_TTL = Thresholds.RECOGNITION_CACHE_TTL
except Exception:
    _RECOGNITION_CACHE_TTL = 5.0

try:
    _MAX_RECOGNITION_RETRIES = Thresholds.MAX_RECOGNITION_RETRIES
except Exception:
    _MAX_RECOGNITION_RETRIES = 3

try:
    _CHECKING_TIMEOUT = Thresholds.CHECKING_TIMEOUT_FRAMES
except Exception:
    _CHECKING_TIMEOUT = 6


def _iou(a, b):
    ix1 = max(a["x"], b["x"])
    iy1 = max(a["y"], b["y"])
    ix2 = min(a["x"] + a["w"], b["x"] + b["w"])
    iy2 = min(a["y"] + a["h"], b["y"] + b["h"])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0


def _nms(faces, iou_thresh=0.3):
    if not faces:
        return []
    faces.sort(key=lambda f: f["x"] + f["y"])
    keep = []
    for f in faces:
        dominated = False
        for k in keep:
            if _iou(f, k) > iou_thresh:
                dominated = True
                break
        if not dominated:
            keep.append(f)
    return keep


# ==========================================================
# YuNet Face Detector
# ==========================================================

_yunet_detector = None


def _get_yunet():
    global _yunet_detector

    if _yunet_detector is None:

        model_path = os.path.join(
            settings.BASE_DIR,
            "models",
            "face_detection_yunet_2023mar.onnx",
        )

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"YuNet model not found: {model_path}"
            )

        _yunet_detector = cv2.FaceDetectorYN_create(
            model=model_path,
            config="",
            input_size=(640, 480),
            score_threshold=0.85,
            nms_threshold=0.3,
            top_k=5000,
        )

    return _yunet_detector


def _is_frontal_face(region):
    w = region["w"]
    h = region["h"]

    if h <= 0:
        return False

    aspect = w / h

    return Thresholds.FRONTAL_ASPECT_MIN <= aspect <= 1.80


def _detect_human_faces(img):
    detector = _get_yunet()
    h_img, w_img = img.shape[:2]
    detector.setInputSize((w_img, h_img))
    _, detections = detector.detect(img)

    if detections is None:
        return []

    faces = []
    for face in detections:
        x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
        score = float(face[-1])
        if score < Thresholds.FACE_VALIDATION_MIN_CONFIDENCE:
            continue
        if w < Thresholds.FACE_VALIDATION_MIN_SIZE or h < Thresholds.FACE_VALIDATION_MIN_SIZE:
            continue
        if not _is_frontal_face({"x": x, "y": y, "w": w, "h": h}):
            continue
        faces.append({"x": x, "y": y, "w": w, "h": h})
    return _nms(faces)


def _live_match_known(emb):
    match, _distance, confidence = RecognitionService.recognize_face_cached(emb)
    return match, confidence


def _recognize_one_face(img, r, w_img, h_img):
    if r["w"] < Thresholds.FACE_VALIDATION_MIN_SIZE or r["h"] < Thresholds.FACE_VALIDATION_MIN_SIZE:
        return None, 0.0

    pad = 0.15
    px = int(r["w"] * pad)
    py = int(r["h"] * pad)
    x1 = max(0, r["x"] - px)
    y1 = max(0, r["y"] - py)
    x2 = min(w_img, r["x"] + r["w"] + px)
    y2 = min(h_img, r["y"] + r["h"] + py)

    if x2 <= x1 or y2 <= y1:
        return None, 0.0

    crop = img[y1:y2, x1:x2]
    if crop is None or crop.size == 0:
        return None, 0.0

    try:
        emb = FaceRecognitionService.get_embedding_live(crop)
        if emb is not None:
            match, confidence = _live_match_known(np.asarray(emb, dtype=np.float32))
            return match, confidence
    except Exception as e:
        logger.debug("Live recognition failed: %s", e)

    return None, 0.0


def _live_recognize(img):
    global _last_labels, _known_label_history, _recognition_frame_counter

    registered = EmbeddingCache.get_all()
    registered_count = len(registered) if registered else 0

    detections = _detect_human_faces(img)
    tracked = _face_tracker.update(detections)
    logger.debug("Live frame: %d detections, %d tracked", len(detections), len(tracked))

    now = time.time()
    active_tids = {face["track_id"] for face in tracked}

    for tid in list(_last_labels.keys()):
        if tid not in active_tids:
            lbl = _last_labels[tid]
            if lbl.get("is_known"):
                cx = lbl.get("region", {}).get("x", 0) + lbl.get("region", {}).get("w", 0) // 2
                cy = lbl.get("region", {}).get("y", 0) + lbl.get("region", {}).get("h", 0) // 2
                _known_label_history.append({
                    "label": lbl["label"],
                    "confidence": lbl["confidence"],
                    "cx": cx, "cy": cy,
                    "time": now,
                })
            del _last_labels[tid]
            _recognition_retries.pop(tid, None)

    _known_label_history = [h for h in _known_label_history if (now - h["time"]) < 5.0]

    if not tracked:
        return [], registered_count

    if registered_count == 0:
        return [{
            "region": face["region"],
            "track_id": face["track_id"],
            "label": "No registered faces",
            "is_known": False,
            "confidence": 0,
            "status": "no_registered",
        } for face in tracked], registered_count

    _recognition_frame_counter += 1
    is_recognition_frame = (_recognition_frame_counter % _RECOGNITION_INTERVAL == 0)

    h_img, w_img = img.shape[:2]

    if is_recognition_frame:
        faces_to_recognize = []
        for face in tracked:
            tid = face["track_id"]
            previous = _last_labels.get(tid)
            if previous:
                if previous["is_known"]:
                    cache_age = now - previous.get("cache_time", 0)
                    if cache_age < _RECOGNITION_CACHE_TTL:
                        continue
                    else:
                        previous["cache_time"] = now
                        continue
                else:
                    retries = _recognition_retries.get(tid, 0)
                    if retries >= _MAX_RECOGNITION_RETRIES:
                        cache_age = previous.get("cache_time", 0)
                        if (now - cache_age) < _RECOGNITION_CACHE_TTL:
                            continue
                        else:
                            _recognition_retries.pop(tid, None)
                            _last_labels.pop(tid, None)
            faces_to_recognize.append(face)

        if faces_to_recognize:
            def _recognize_wrapper(face):
                return face["track_id"], _recognize_one_face(img, face["region"], w_img, h_img)

            max_workers = min(len(faces_to_recognize), 4)
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_recognize_wrapper, f): f for f in faces_to_recognize}
                for future in as_completed(futures):
                    tid, (match, conf) = future.result()
                    if match:
                        _recognition_retries.pop(tid, None)
                        _last_labels[tid] = {
                            "label": match["name"], "is_known": True,
                            "confidence": conf, "status": "recognized",
                            "cache_time": now,
                            "region": next((f["region"] for f in tracked if f["track_id"] == tid), {}),
                        }
                    else:
                        retries = _recognition_retries.get(tid, 0) + 1
                        _recognition_retries[tid] = retries
                        region = next((f["region"] for f in tracked if f["track_id"] == tid), {})
                        if retries < _MAX_RECOGNITION_RETRIES:
                            _last_labels[tid] = {
                                "label": "", "is_known": False,
                                "confidence": 0, "status": "checking",
                                "cache_time": now,
                                "region": region,
                            }
                        else:
                            _recognition_retries.pop(tid, None)
                            _last_labels[tid] = {
                                "label": "Unknown", "is_known": False,
                                "confidence": conf, "status": "unknown",
                                "cache_time": now,
                                "region": region,
                            }

    results = []
    for face in tracked:
        tid = face["track_id"]
        reco = _last_labels.get(tid)
        if reco:
            reco["region"] = face["region"]
            results.append({
                "region": face["region"],
                "track_id": tid,
                "label": reco["label"],
                "is_known": reco["is_known"],
                "confidence": reco["confidence"],
                "status": reco["status"],
            })
        else:
            region = face["region"]
            _last_labels[tid] = {
                "label": "", "is_known": False,
                "confidence": 0, "status": "checking",
                "cache_time": now,
                "region": region,
            }
            results.append({
                "region": region,
                "track_id": tid,
                "label": "",
                "is_known": False,
                "confidence": 0,
                "status": "checking",
            })
    return results, registered_count


def _try_recover_label(region):
    if not _known_label_history or not region:
        return None
    cx = region.get("x", 0) + region.get("w", 0) // 2
    cy = region.get("y", 0) + region.get("h", 0) // 2
    now = time.time()
    best = None
    best_dist = float("inf")
    for h in _known_label_history:
        if (now - h["time"]) > 2.0:
            continue
        if h.get("confidence", 0) < 80:
            continue
        dx = cx - h["cx"]
        dy = cy - h["cy"]
        d = (dx * dx + dy * dy) ** 0.5
        if d < best_dist:
            best_dist = d
            best = h
    if best and best_dist < 60:
        logger.debug("Label recovered: '%s' at dist=%.0f (conf=%.1f%%)",
                      best["label"], best_dist, best["confidence"])
        return {"label": best["label"], "confidence": best["confidence"]}
    return None

@api_view(["POST"])
def live_detect(request):
    t0 = time.time()
    try:
        file = request.FILES.get("image")
        if not file:
            return Response({"success": False, "message": "No image provided."}, status=status.HTTP_400_BAD_REQUEST)
        raw = file.read()
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return Response({"success": False, "message": "Invalid image."}, status=status.HTTP_400_BAD_REQUEST)
        img = ImagePreprocessor.auto_resize_numpy(img)
        results, registered_count = _live_recognize(img)
        latency_ms = round((time.time() - t0) * 1000)
        logger.info("Live detect: %d face(s), %d registered, %dms", len(results), registered_count, latency_ms)
        return Response({
            "success": True,
            "face_count": len(results),
            "faces": results,
            "registered_faces": registered_count,
            "latency_ms": round((time.time() - t0) * 1000),
        })
    except Exception as e:
        logger.exception("Live detect failed")
        return Response({
            "success": False, "message": str(e), "faces": [],
            "latency_ms": round((time.time() - t0) * 1000),
        })


_capture_cooldown = {}

@api_view(["POST"])
def live_capture(request):
    t0 = time.time()
    try:
        file = request.FILES.get("image")
        if not file:
            return Response({"success": False, "message": "No image provided."}, status=status.HTTP_400_BAD_REQUEST)
        raw = file.read()
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return Response({"success": False, "message": "Invalid image."}, status=status.HTTP_400_BAD_REQUEST)
        img = ImagePreprocessor.auto_resize_numpy(img)
        results, registered_count = _live_recognize(img)
        faces = []
        image_record = None
        captures = 0
        for r in results:
            region = r.get("region", {})
            label = r.get("label", "Unknown")
            is_known = r.get("is_known", False)
            match_confidence = r.get("confidence", 0)
            face_status = r.get("status", "unknown")
            known_face_obj = None
            if is_known:
                try:
                    known_face_obj = KnownFace.objects.get(name=label)
                except KnownFace.DoesNotExist:
                    pass
            now = time.time()
            cooldown_key = label if is_known else "unknown"
            last_cap = _capture_cooldown.get(cooldown_key, 0)
            captured = (now - last_cap) > 5
            if captured:
                _capture_cooldown[cooldown_key] = now
                captures += 1
                if image_record is None:
                    image_record = UploadedImage.objects.create(user=request.user)
                    image_record.image.save(f"capture_{uuid.uuid4().hex}.jpg", ContentFile(raw), save=True)
                    image_record.width = img.shape[1]
                    image_record.height = img.shape[0]
                    image_record.save(update_fields=["width", "height"])
                detected_face = DetectedFace.objects.create(
                    image=image_record, bounding_box=region, face_confidence=0,
                )
                RecognitionLog.objects.create(
                    detected_face=detected_face, matched_face=known_face_obj,
                    confidence=match_confidence, is_known=is_known,
                )
            faces.append({
                "region": region, "label": label, "is_known": is_known,
                "confidence": match_confidence, "captured": captured,
                "status": face_status,
            })
        latency_ms = round((time.time() - t0) * 1000)
        logger.info("Live capture: %d face(s), %d captured, %d registered, %dms",
                     len(faces), captures, registered_count, latency_ms)
        return Response({
            "success": True, "face_count": len(faces), "faces": faces,
            "registered_faces": registered_count,
            "latency_ms": latency_ms,
        })
    except Exception as e:
        logger.exception("Live capture failed")
        return Response({
            "success": False, "message": str(e), "faces": [],
            "latency_ms": round((time.time() - t0) * 1000),
        })


@api_view(["GET"])
def get_face_detail(request, pk):
    try:
        face = DetectedFace.objects.get(id=pk, image__user=request.user)
    except DetectedFace.DoesNotExist:
        return Response({"success": False, "message": "Face not found."}, status=status.HTTP_404_NOT_FOUND)
    serializer = DetectedFaceSerializer(face)
    return Response({"success": True, "data": serializer.data})
