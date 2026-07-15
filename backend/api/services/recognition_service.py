import numpy as np
from api.models import KnownFace, FaceImage
from api.config.thresholds import Thresholds
from .face_recognition_service import FaceRecognitionService
from .embedding_cache import EmbeddingCache


class RecognitionService:

    SIMILARITY_THRESHOLD = Thresholds.SIMILARITY_THRESHOLD
    CONFIDENCE_THRESHOLD = Thresholds.CONFIDENCE_THRESHOLD

    @classmethod
    def recognize_face(cls, embedding):
        if not embedding:
            return None, 0.0, 0.0

        known_faces = KnownFace.objects.filter(
            user__isnull=False, face_images__embedding__isnull=False
        ).distinct()

        if not known_faces.exists():
            return None, 0.0, 0.0

        best_match = None
        best_distance = float("inf")

        for known in known_faces:
            images = known.face_images.exclude(embedding__isnull=True)
            if not images.exists():
                continue

            _, min_dist, _ = FaceRecognitionService.find_best_match(embedding, images)

            if min_dist < best_distance:
                best_distance = min_dist
                best_match = known

        if best_match is None:
            return None, 0.0, 0.0

        confidence = max(0.0, min(100.0, (1.0 - best_distance) * 100.0))

        if best_distance < cls.SIMILARITY_THRESHOLD and confidence >= cls.CONFIDENCE_THRESHOLD:
            return best_match, round(best_distance, 4), round(confidence, 2)

        return None, round(best_distance, 4), round(confidence, 2)

    @classmethod
    def recognize_face_cached(cls, embedding):
        if not embedding:
            return None, 0.0, 0.0

        cached = EmbeddingCache.get_all()
        if not cached:
            return None, 0.0, 0.0

        emb_array = np.asarray(embedding, dtype=np.float32)
        emb_norm = emb_array / np.linalg.norm(emb_array)

        best_match_name = None
        best_match_id = None
        best_distance = float("inf")
        second_best_distance = float("inf")

        for entry in cached:
            for known_emb in entry["embeddings"]:
                known_array = np.asarray(known_emb, dtype=np.float32)
                known_norm = known_array / np.linalg.norm(known_array)
                dist = float(1.0 - np.dot(emb_norm, known_norm))
                if dist < best_distance:
                    second_best_distance = best_distance
                    best_distance = dist
                    best_match_name = entry["name"]
                    best_match_id = entry["id"]
                elif dist < second_best_distance:
                    second_best_distance = dist

        if best_match_name is None:
            return None, 0.0, 0.0

        confidence = max(0.0, min(100.0, (1.0 - best_distance) * 100.0))

        margin = second_best_distance - best_distance

        if (best_distance < cls.SIMILARITY_THRESHOLD
                and confidence >= cls.CONFIDENCE_THRESHOLD
                and margin > Thresholds.LIVE_MATCH_MARGIN):
            return {"id": best_match_id, "name": best_match_name}, round(best_distance, 4), round(confidence, 2)

        return None, round(best_distance, 4), round(confidence, 2)

    @classmethod
    def verify_pair(cls, img1_path, img2_path):
        emb1 = FaceRecognitionService.get_embedding(img1_path)
        emb2 = FaceRecognitionService.get_embedding(img2_path)
        if not emb1 or not emb2:
            return {"verified": False, "distance": None, "error": "Could not extract embeddings"}
        distance = FaceRecognitionService.compute_distance(emb1, emb2)
        confidence = FaceRecognitionService.compute_confidence(emb1, emb2)
        threshold = cls.SIMILARITY_THRESHOLD
        return {
            "verified": distance < threshold,
            "distance": round(distance, 4),
            "confidence": round(confidence, 2),
            "threshold": threshold,
        }
