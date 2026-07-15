import os
import cv2
import numpy as np
from deepface import DeepFace
from api.config.thresholds import Thresholds


class FaceRecognitionService:
    MODEL_NAME = "Facenet"
    MATCH_THRESHOLD = Thresholds.SIMILARITY_THRESHOLD

    @staticmethod
    def preprocess_image(image_path):
        image = cv2.imread(image_path)

        if image is None:
            return image_path

        h, w = image.shape[:2]

        if max(h, w) > 1000:
            scale = 1000 / max(h, w)
            image = cv2.resize(
                image,
                (int(w * scale), int(h * scale))
            )

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        l = clahe.apply(l)

        image = cv2.cvtColor(
            cv2.merge((l, a, b)),
            cv2.COLOR_LAB2BGR
        )

        temp_path = image_path.replace(
            ".jpg",
            "_temp.jpg"
        ).replace(
            ".png",
            "_temp.png"
        )

        cv2.imwrite(temp_path, image)

        return temp_path

    @classmethod
    def get_embedding(cls, image_source, detector_backend="mtcnn"):
        """Accepts a file path (str) or a numpy array (BGR)."""

        temp_path = None

        try:

            embedding = DeepFace.represent(
                img_path=image_source,
                model_name=cls.MODEL_NAME,
                detector_backend=detector_backend,
                enforce_detection=False
            )

        except Exception:

            if isinstance(image_source, str):
                temp_path = cls.preprocess_image(image_source)
                img_arg = temp_path
            else:
                temp_path = cls._temp_npy(image_source)
                img_arg = temp_path

            embedding = DeepFace.represent(
                img_path=img_arg,
                model_name=cls.MODEL_NAME,
                detector_backend=detector_backend,
                enforce_detection=False
            )

        finally:

            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

        if not embedding:
            return None

        vector = embedding[0]["embedding"]

        vector = np.asarray(vector, dtype=np.float32)

        vector = vector / np.linalg.norm(vector)

        return vector.tolist()

    @staticmethod
    def _temp_npy(img_array):
        import uuid, tempfile
        fd, path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        cv2.imwrite(path, img_array)
        return path

    @staticmethod
    def cosine_similarity(a, b):

        a = np.asarray(a)

        b = np.asarray(b)

        return float(
            np.dot(a, b) /
            (np.linalg.norm(a) * np.linalg.norm(b))
        )

    @classmethod
    def compute_distance(cls, emb1, emb2):

        similarity = cls.cosine_similarity(
            emb1,
            emb2
        )

        return 1 - similarity

    @classmethod
    def compute_confidence(cls, emb1, emb2):

        similarity = cls.cosine_similarity(
            emb1,
            emb2
        )

        confidence = similarity * 100

        confidence = max(0, min(100, confidence))

        return round(confidence, 2)

    @classmethod
    def find_best_match(cls, query_embedding, known_faces):

        best_face = None
        best_distance = 999

        for face in known_faces:

            if not face.embedding:
                continue

            distance = cls.compute_distance(
                query_embedding,
                face.embedding
            )

            if distance < best_distance:

                best_distance = distance

                best_face = face

        if best_face is None:
            return None, 0, 0

        confidence = cls.compute_confidence(
            query_embedding,
            best_face.embedding
        )

        if best_distance > cls.MATCH_THRESHOLD:

            return None, round(best_distance, 4), confidence

        return (
            best_face,
            round(best_distance, 4),
            confidence
        )