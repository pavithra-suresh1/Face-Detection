import cv2
import numpy as np
import tempfile
import os

from retinaface import RetinaFace
from api.config.thresholds import Thresholds


class RetinaFaceService:

    @staticmethod
    def detect_faces(image):

        temp_file = None

        try:
            # Accept both file path and OpenCV frame
            if isinstance(image, np.ndarray):
                fd, temp_file = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                cv2.imwrite(temp_file, image)
                source = temp_file
            else:
                source = image

            faces = RetinaFace.detect_faces(source)

            if not faces or not isinstance(faces, dict):
                return []

            result = []

            for _, face_data in faces.items():

                if not isinstance(face_data, dict):
                    continue

                score = float(face_data.get("score", 0))

                if score < Thresholds.RETINAFACE_MIN_CONFIDENCE:
                    continue

                x1, y1, x2, y2 = face_data["facial_area"]

                w = x2 - x1
                h = y2 - y1

                # Ignore tiny detections
                if w < 80 or h < 80:
                    continue

                # Expand face region
                pad_x = int(w * 0.20)
                pad_y = int(h * 0.25)

                x1 = max(0, x1 - pad_x)
                y1 = max(0, y1 - pad_y)

                w = w + pad_x * 2
                h = h + pad_y * 2

                result.append({
                    "region": {
                        "x": int(x1),
                        "y": int(y1),
                        "w": int(w),
                        "h": int(h),
                    },
                    "confidence": round(score, 4),
                    "landmarks": face_data.get("landmarks"),
                })

            return result

        finally:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)

    @staticmethod
    def crop_faces(image, faces):

        if isinstance(image, str):
            image = cv2.imread(image)

        if image is None:
            return []

        img_h, img_w = image.shape[:2]

        crops = []

        for face in faces:

            r = face["region"]

            x = max(0, r["x"])
            y = max(0, r["y"])

            w = min(r["w"], img_w - x)
            h = min(r["h"], img_h - y)

            crop = image[y:y+h, x:x+w]

            if crop.size == 0:
                continue

            crops.append(crop)

        return crops