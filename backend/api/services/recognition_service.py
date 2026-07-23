import logging
import numpy as np
from api.models import KnownFace, FaceImage
from api.config.thresholds import Thresholds
from .face_recognition_service import FaceRecognitionService
from .embedding_cache import EmbeddingCache
from api.utils.preprocessing import EmbeddingNormalizer

logger = logging.getLogger(__name__)


class RecognitionService:

    SIMILARITY_THRESHOLD = Thresholds.SIMILARITY_THRESHOLD
    CONFIDENCE_THRESHOLD = Thresholds.CONFIDENCE_THRESHOLD

    @classmethod
    def recognize_face(cls, embedding):
        if embedding is None:
            return None, 0.0, 0.0

        embedding = EmbeddingNormalizer.normalize_l2(embedding).tolist()

        known_faces = KnownFace.objects.filter(
            user__isnull=False, face_images__embedding__isnull=False
        ).distinct()

        if not known_faces.exists():
            return None, 0.0, 0.0

        best_match = None
        best_distance = float("inf")
        second_best_distance = float("inf")

        for known in known_faces:
            images = known.face_images.exclude(embedding__isnull=True)
            if not images.exists():
                continue

            _, min_dist, _, _ = FaceRecognitionService.find_best_match(embedding, images)

            if min_dist < best_distance:
                second_best_distance = best_distance
                best_distance = min_dist
                best_match = known
            elif min_dist < second_best_distance:
                second_best_distance = min_dist

        if best_match is None:
            return None, 0.0, 0.0

        confidence = max(0.0, min(100.0, (1.0 - best_distance) * 100.0))
        margin = second_best_distance - best_distance

        similarity_ok = best_distance < cls.SIMILARITY_THRESHOLD
        confidence_ok = confidence >= cls.CONFIDENCE_THRESHOLD
        margin_ok = len(known_faces) <= 1 or margin > Thresholds.LIVE_MATCH_MARGIN

        if similarity_ok and confidence_ok and margin_ok:
            logger.debug("DB match: name=%s, distance=%.4f, confidence=%.2f, margin=%.4f",
                          best_match.name, best_distance, confidence, margin)
            return best_match, round(best_distance, 4), round(confidence, 2)

        logger.debug("DB match rejected: distance=%.4f, confidence=%.2f, margin=%.4f",
                      best_distance, confidence, margin)
        return None, round(best_distance, 4), round(confidence, 2)

    @classmethod
    def recognize_face_cached(cls, embedding):
        if embedding is None:
            return None, 0.0, 0.0

        cached = EmbeddingCache.get_all()
        if not cached:
            return None, 0.0, 0.0

        emb_norm = EmbeddingNormalizer.normalize_l2(embedding)

        avg_matrix, ind_matrix, ind_person_idx = EmbeddingCache.get_matrices()

        if avg_matrix is not None and avg_matrix.shape[0] > 0:
            emb_vec = np.asarray(emb_norm, dtype=np.float32).reshape(1, -1)
            avg_dists = 1.0 - emb_vec.dot(avg_matrix.T)
            avg_dists = avg_dists.flatten()
        else:
            avg_dists = np.empty(0, dtype=np.float32)

        best_ind_dist_per_person = np.full(len(cached), float("inf"), dtype=np.float32)
        verified_counts = np.zeros(len(cached), dtype=np.int32)

        if ind_matrix is not None and ind_matrix.shape[0] > 0:
            emb_vec = np.asarray(emb_norm, dtype=np.float32).reshape(1, -1)
            ind_dists = 1.0 - emb_vec.dot(ind_matrix.T)
            ind_dists = ind_dists.flatten()

            for i, pidx in enumerate(ind_person_idx):
                d = float(ind_dists[i])
                if d < best_ind_dist_per_person[pidx]:
                    best_ind_dist_per_person[pidx] = d

            tol = Thresholds.MATCH_INDIVIDUAL_TOLERANCE
            for pidx in range(len(cached)):
                mask = ind_person_idx == pidx
                p_dists = ind_dists[mask]
                if len(p_dists) > 0:
                    bdist = best_ind_dist_per_person[pidx]
                    verified_counts[pidx] = int(np.sum(p_dists <= bdist + tol))

        candidates = []
        for i in range(len(cached)):
            entry = cached[i]
            avg_dist = float(avg_dists[i]) if i < len(avg_dists) else float("inf")
            best_ind = float(best_ind_dist_per_person[i])
            vc = int(verified_counts[i])

            use_individual = (
                best_ind < avg_dist
                and vc >= Thresholds.MATCH_MIN_VERIFIED_IMAGES
            )
            final_dist = best_ind if use_individual else avg_dist

            candidates.append({
                "id": entry["id"],
                "name": entry["name"],
                "final_dist": final_dist,
            })

        if not candidates:
            return None, 0.0, 0.0

        candidates.sort(key=lambda c: c["final_dist"])
        best = candidates[0]
        second_dist = candidates[1]["final_dist"] if len(candidates) >= 2 else best["final_dist"] + 1.0

        confidence = max(0.0, min(100.0, (1.0 - best["final_dist"]) * 100.0))
        margin = second_dist - best["final_dist"]

        similarity_ok = best["final_dist"] < cls.SIMILARITY_THRESHOLD
        confidence_ok = confidence >= cls.CONFIDENCE_THRESHOLD
        margin_ok = len(candidates) <= 1 or margin > Thresholds.LIVE_MATCH_MARGIN

        if similarity_ok and confidence_ok and margin_ok:
            logger.info("Match ACCEPTED: name=%s, dist=%.4f, confidence=%.1f%%, margin=%.4f",
                        best["name"], best["final_dist"], confidence, margin)
            return {"id": best["id"], "name": best["name"]}, round(best["final_dist"], 4), round(confidence, 2)

        reasons = []
        if not similarity_ok:
            reasons.append(f"distance={best['final_dist']:.4f} >= threshold={cls.SIMILARITY_THRESHOLD}")
        if not confidence_ok:
            reasons.append(f"confidence={confidence:.1f}% < min={cls.CONFIDENCE_THRESHOLD}%")
        if not margin_ok:
            reasons.append(f"margin={margin:.4f} <= min={Thresholds.LIVE_MATCH_MARGIN}")
        logger.info("Match REJECTED: best='%s' dist=%.4f, confidence=%.1f%%, margin=%.4f | %s",
                     best["name"], best["final_dist"], confidence, margin, "; ".join(reasons))
        return None, round(best["final_dist"], 4), round(confidence, 2)

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
