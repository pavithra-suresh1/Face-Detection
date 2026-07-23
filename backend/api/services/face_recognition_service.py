import logging
import os
import cv2
import numpy as np
from deepface import DeepFace
from api.config.thresholds import Thresholds
from api.utils.preprocessing import ImagePreprocessor
from api.utils.preprocessing import EmbeddingNormalizer

logger = logging.getLogger(__name__)


class FaceRecognitionService:
    MODEL_NAME = "Facenet"
    MATCH_THRESHOLD = Thresholds.SIMILARITY_THRESHOLD
    _live_detector = None

    @staticmethod
    def preprocess_image(image_path):
        image = cv2.imread(image_path)

        if image is None:
            return image_path

        image = ImagePreprocessor.auto_resize_numpy(image)
        image = ImagePreprocessor.clahe_enhance(image)

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
        temp_path = None

        try:
            embedding = DeepFace.represent(
                img_path=image_source,
                model_name=cls.MODEL_NAME,
                detector_backend=detector_backend,
                enforce_detection=False
            )

        except Exception:
            logger.debug("Primary embedding failed for %s, trying CLAHE preprocess", image_source)
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
            logger.warning("No embedding extracted from %s", image_source)
            return None

        vector = embedding[0]["embedding"]

        vector = EmbeddingNormalizer.normalize_l2(vector)

        return vector.tolist()

    @classmethod
    def get_embedding_live(cls, crop_bgr):
        try:
            detector_backend = Thresholds.EMBEDDING_DETECTOR_BACKEND
        except Exception:
            detector_backend = "opencv"

        try:
            _, buf = cv2.imencode('.jpg', crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
            img_bytes = buf.tobytes()

            embedding = DeepFace.represent(
                img_path=img_bytes,
                model_name=cls.MODEL_NAME,
                detector_backend=detector_backend,
                enforce_detection=False,
            )
            if not embedding:
                return None
            vector = embedding[0]["embedding"]
            return EmbeddingNormalizer.normalize_l2(vector).tolist()
        except Exception as e:
            logger.debug("Live embedding failed with %s, trying mtcnn fallback: %s", detector_backend, e)
            try:
                import tempfile
                fd, temp_path = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                cv2.imwrite(temp_path, crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
                embedding = DeepFace.represent(
                    img_path=temp_path,
                    model_name=cls.MODEL_NAME,
                    detector_backend="mtcnn",
                    enforce_detection=False,
                )
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
                if not embedding:
                    return None
                vector = embedding[0]["embedding"]
                return EmbeddingNormalizer.normalize_l2(vector).tolist()
            except Exception as e2:
                logger.debug("Live embedding fallback also failed: %s", e2)
                return None

    @staticmethod
    def _temp_npy(img_array):
        import uuid, tempfile
        fd, path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        cv2.imwrite(path, img_array)
        return path

    @staticmethod
    def cosine_similarity(a, b):

        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)

        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)

        if a_norm > 0:
            a = a / a_norm
        if b_norm > 0:
            b = b / b_norm

        return float(np.dot(a, b))

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
        second_distance = 999

        for face in known_faces:

            if not face.embedding:
                continue

            distance = cls.compute_distance(
                query_embedding,
                face.embedding
            )

            if distance < best_distance:
                second_distance = best_distance
                best_distance = distance
                best_face = face
            elif distance < second_distance:
                second_distance = distance

        if best_face is None:
            return None, 0, 0, 0

        confidence = cls.compute_confidence(
            query_embedding,
            best_face.embedding
        )

        if best_distance > cls.MATCH_THRESHOLD:

            return None, round(best_distance, 4), confidence, round(second_distance, 4)

        return (
            best_face,
            round(best_distance, 4),
            confidence,
            round(second_distance, 4)
        )
