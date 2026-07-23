import logging
import os
import cv2
import numpy as np
from PIL import Image, ImageOps
from api.config.thresholds import Thresholds

logger = logging.getLogger(__name__)


class ImageQualityValidator:

    @staticmethod
    def check_blur(gray):
        try:
            if gray is None:
                return False, 0.0
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()
            is_blurry = variance < Thresholds.QUALITY_BLUR_THRESHOLD
            return is_blurry, round(float(variance), 2)
        except Exception:
            return False, 0.0

    @staticmethod
    def check_brightness(gray):
        try:
            if gray is None:
                return None, 0.0
            mean_brightness = float(np.mean(gray))
            if mean_brightness < Thresholds.QUALITY_DARK_THRESHOLD:
                return "dark", round(mean_brightness, 2)
            if mean_brightness > Thresholds.QUALITY_BRIGHT_THRESHOLD:
                return "overexposed", round(mean_brightness, 2)
            return "ok", round(mean_brightness, 2)
        except Exception:
            return None, 0.0

    @staticmethod
    def check_resolution(img):
        try:
            if img is None:
                return False, 0, 0
            h, w = img.shape[:2]
            is_too_small = (w < Thresholds.QUALITY_MIN_RESOLUTION or h < Thresholds.QUALITY_MIN_RESOLUTION)
            return is_too_small, w, h
        except Exception:
            return False, 0, 0

    @classmethod
    def validate(cls, image_path):
        issues = []

        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None

        is_blurry, blur_score = cls.check_blur(gray)
        if is_blurry:
            logger.debug("Quality check '%s': blurry (score=%.2f, threshold=%.2f)",
                          image_path, blur_score, Thresholds.QUALITY_BLUR_THRESHOLD)
            issues.append({
                "type": "blurry",
                "message": "Image is too blurry for reliable face detection.",
                "score": blur_score,
                "threshold": Thresholds.QUALITY_BLUR_THRESHOLD,
            })

        brightness_status, brightness_value = cls.check_brightness(gray)
        if brightness_status == "dark":
            logger.debug("Quality check '%s': too dark (brightness=%.2f, threshold=%.2f)",
                          image_path, brightness_value, Thresholds.QUALITY_DARK_THRESHOLD)
            issues.append({
                "type": "too_dark",
                "message": "Image is too dark. Try a brighter photo.",
                "score": brightness_value,
                "threshold": Thresholds.QUALITY_DARK_THRESHOLD,
            })
        elif brightness_status == "overexposed":
            logger.debug("Quality check '%s': overexposed (brightness=%.2f, threshold=%.2f)",
                          image_path, brightness_value, Thresholds.QUALITY_BRIGHT_THRESHOLD)
            issues.append({
                "type": "overexposed",
                "message": "Image is overexposed. Try a photo with less brightness.",
                "score": brightness_value,
                "threshold": Thresholds.QUALITY_BRIGHT_THRESHOLD,
            })

        is_small, w, h = cls.check_resolution(img)
        if is_small:
            logger.debug("Quality check '%s': low resolution (%dx%d, min=%d)",
                          image_path, w, h, Thresholds.QUALITY_MIN_RESOLUTION)
            issues.append({
                "type": "low_resolution",
                "message": f"Image resolution is too low ({w}x{h}). Minimum is {Thresholds.QUALITY_MIN_RESOLUTION}x{Thresholds.QUALITY_MIN_RESOLUTION}.",
                "width": w,
                "height": h,
            })

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    @classmethod
    def validate_with_image(cls, img):
        """Validate quality using a pre-loaded BGR image (avoids re-reading from disk)."""
        issues = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img is not None else None

        is_blurry, blur_score = cls.check_blur(gray)
        if is_blurry:
            issues.append({
                "type": "blurry",
                "message": "Image is too blurry for reliable face detection.",
                "score": blur_score,
                "threshold": Thresholds.QUALITY_BLUR_THRESHOLD,
            })

        brightness_status, brightness_value = cls.check_brightness(gray)
        if brightness_status == "dark":
            issues.append({
                "type": "too_dark",
                "message": "Image is too dark. Try a brighter photo.",
                "score": brightness_value,
                "threshold": Thresholds.QUALITY_DARK_THRESHOLD,
            })
        elif brightness_status == "overexposed":
            issues.append({
                "type": "overexposed",
                "message": "Image is overexposed. Try a photo with less brightness.",
                "score": brightness_value,
                "threshold": Thresholds.QUALITY_BRIGHT_THRESHOLD,
            })

        is_small, w, h = cls.check_resolution(img)
        if is_small:
            issues.append({
                "type": "low_resolution",
                "message": f"Image resolution is too low ({w}x{h}). Minimum is {Thresholds.QUALITY_MIN_RESOLUTION}x{Thresholds.QUALITY_MIN_RESOLUTION}.",
                "width": w,
                "height": h,
            })

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    @classmethod
    def validate_strict(cls, image_path):
        result = cls.validate(image_path)
        if not result["valid"]:
            messages = [i["message"] for i in result["issues"]]
            raise ValueError("; ".join(messages))
        return True


class FaceValidator:

    @staticmethod
    def _face_area(region):
        return region["w"] * region["h"]

    @classmethod
    def validate_faces(cls, detected_faces):
        issues = []

        if not detected_faces:
            issues.append({
                "type": "no_face",
                "message": "No face detected in the image. Please upload a clear photo with a visible face.",
            })
            return {"valid": False, "issues": issues, "selected_face": None}

        if len(detected_faces) > 1:
            issues.append({
                "type": "multiple_faces",
                "message": f"Found {len(detected_faces)} faces. Please upload an image with exactly one face.",
                "face_count": len(detected_faces),
            })

        undersized = []
        low_confidence = []
        valid_faces = []

        for i, face in enumerate(detected_faces):
            region = face.get("region", {})
            confidence = face.get("confidence", 0)
            area = cls._face_area(region)
            min_area = Thresholds.FACE_VALIDATION_MIN_SIZE ** 2

            if area < min_area:
                undersized.append({
                    "index": i,
                    "area": area,
                    "min_area": min_area,
                    "width": region.get("w", 0),
                    "height": region.get("h", 0),
                })
                continue

            if confidence < Thresholds.FACE_VALIDATION_MIN_CONFIDENCE:
                low_confidence.append({
                    "index": i,
                    "confidence": confidence,
                    "threshold": Thresholds.FACE_VALIDATION_MIN_CONFIDENCE,
                })
                continue

            valid_faces.append((i, face))

        if undersized:
            smallest = min(undersized, key=lambda x: x["area"])
            issues.append({
                "type": "face_too_small",
                "message": (
                    f"Face is too small ({smallest['width']}x{smallest['height']}px). "
                    f"Minimum face size is {Thresholds.FACE_VALIDATION_MIN_SIZE}x{Thresholds.FACE_VALIDATION_MIN_SIZE}px. "
                    "Try a closer photo."
                ),
                "min_size": Thresholds.FACE_VALIDATION_MIN_SIZE,
            })

        if low_confidence:
            worst = min(low_confidence, key=lambda x: x["confidence"])
            issues.append({
                "type": "low_face_confidence",
                "message": (
                    f"Face detection confidence is too low ({worst['confidence']:.0%}). "
                    f"Minimum is {Thresholds.FACE_VALIDATION_MIN_CONFIDENCE:.0%}. "
                    "Try a clearer, front-facing photo."
                ),
                "confidence": worst["confidence"],
                "threshold": Thresholds.FACE_VALIDATION_MIN_CONFIDENCE,
            })

        is_valid = len(issues) == 0 and len(valid_faces) == 1
        selected = valid_faces[0][1] if valid_faces else None

        return {
            "valid": is_valid,
            "issues": issues,
            "selected_face": selected,
            "valid_face_count": len(valid_faces),
        }

    @classmethod
    def validate_faces_strict(cls, detected_faces):
        result = cls.validate_faces(detected_faces)
        if not result["valid"]:
            messages = [i["message"] for i in result["issues"]]
            raise ValueError("; ".join(messages))
        return result["selected_face"]


class ImagePreprocessor:

    @staticmethod
    def fix_exif_orientation(image_path):
        try:
            with Image.open(image_path) as img:
                corrected = ImageOps.exif_transpose(img)
                if corrected is None:
                    return image_path
                corrected.save(image_path, quality=95)
                return image_path
        except Exception:
            return image_path

    @staticmethod
    def fix_exif_orientation_pil(img):
        try:
            return ImageOps.exif_transpose(img) or img
        except Exception:
            return img

    @staticmethod
    def auto_resize(image_path, max_dim=None):
        max_dim = max_dim or Thresholds.PREPROCESS_MAX_DIMENSION

        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            h, w = img.shape[:2]
            if max(h, w) <= max_dim:
                return image_path

            scale = max_dim / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

            ext = os.path.splitext(image_path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                cv2.imwrite(image_path, resized, [cv2.IMWRITE_JPEG_QUALITY, 95])
            elif ext == ".png":
                cv2.imwrite(image_path, resized, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            else:
                cv2.imwrite(image_path, resized, [cv2.IMWRITE_JPEG_QUALITY, 95])

            return image_path
        except Exception:
            return image_path

    @staticmethod
    def auto_resize_numpy(img, max_dim=None):
        max_dim = max_dim or Thresholds.PREPROCESS_MAX_DIMENSION
        h, w = img.shape[:2]
        if max(h, w) <= max_dim:
            return img
        scale = max_dim / max(h, w)
        return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    @staticmethod
    def to_rgb(image_path):
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            if len(img.shape) == 2:
                rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            elif img.shape[2] == 4:
                rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            else:
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            return rgb
        except Exception:
            return image_path

    @staticmethod
    def to_rgb_numpy(img):
        if img is None:
            return img
        if len(img.shape) == 2:
            return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        if img.shape[2] == 4:
            return cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    @staticmethod
    def normalize(img):
        if img is None:
            return img
        return img.astype(np.float32) / 255.0

    @classmethod
    def preprocess_for_detection(cls, image_path):
        image_path = cls.fix_exif_orientation(image_path)
        image_path = cls.auto_resize(image_path)
        return image_path

    @classmethod
    def preprocess_frame(cls, frame):
        frame = cls.auto_resize_numpy(frame)
        frame = cls.to_rgb_numpy(frame)
        return frame

    @classmethod
    def preprocess_for_embedding(cls, image_path):
        image_path = cls.fix_exif_orientation(image_path)
        image_path = cls.auto_resize(image_path)
        img = cls.to_rgb(image_path)
        if isinstance(img, str):
            return image_path
        return img

    @staticmethod
    def clahe_enhance(img):
        if img is None:
            return img
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(
            clipLimit=Thresholds.CLAHE_CLIP_LIMIT,
            tileGridSize=Thresholds.CLAHE_TILE_SIZE,
        )
        l = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


class EmbeddingNormalizer:

    @staticmethod
    def normalize_l2(vector):
        arr = np.asarray(vector, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return arr
        return arr / norm

    @classmethod
    def normalize_list(cls, embeddings):
        return [cls.normalize_l2(emb).tolist() for emb in embeddings]

    @staticmethod
    def is_normalized(vector, atol=1e-3):
        arr = np.asarray(vector, dtype=np.float32)
        norm = np.linalg.norm(arr)
        return abs(norm - 1.0) < atol

    @staticmethod
    def dot_distance(emb_a, emb_b):
        a = np.asarray(emb_a, dtype=np.float32)
        b = np.asarray(emb_b, dtype=np.float32)
        return float(1.0 - np.dot(a, b))
