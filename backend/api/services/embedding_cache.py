import logging
import threading
import numpy as np
from api.models import KnownFace, FaceImage
from api.utils.preprocessing import EmbeddingNormalizer

logger = logging.getLogger(__name__)


class EmbeddingCache:
    _lock = threading.Lock()
    _cache = []
    _avg_matrix = None
    _ind_matrix = None
    _ind_person_ids = []
    _ind_person_idx = []

    @classmethod
    def get_all(cls):
        with cls._lock:
            return cls._cache

    @classmethod
    def get_matrices(cls):
        with cls._lock:
            return cls._avg_matrix, cls._ind_matrix, cls._ind_person_idx

    @classmethod
    def _build(cls):
        known_faces = KnownFace.objects.filter(
            face_images__embedding__isnull=False
        ).prefetch_related("face_images").distinct()

        cache = []
        all_averaged = []
        all_ind_normalized = []
        ind_person_idx = []
        person_idx_map = {}

        for face in known_faces:
            embeddings = []
            normalized = []
            for img in face.face_images.all():
                if img.embedding:
                    arr = np.asarray(img.embedding, dtype=np.float32)
                    normalized_vec = EmbeddingNormalizer.normalize_l2(arr)
                    embeddings.append(img.embedding)
                    normalized.append(normalized_vec.tolist())

            if embeddings:
                all_norm = np.asarray(normalized, dtype=np.float32)
                mean_vec = np.mean(all_norm, axis=0)
                averaged = EmbeddingNormalizer.normalize_l2(mean_vec).tolist()

                cache.append({
                    "id": str(face.id),
                    "name": face.name,
                    "embeddings": embeddings,
                    "normalized": normalized,
                    "averaged": averaged,
                    "image_count": len(embeddings),
                })

                pidx = len(person_idx_map)
                person_idx_map[str(face.id)] = pidx
                all_averaged.append(averaged)

                for n_vec in normalized:
                    all_ind_normalized.append(n_vec)
                    ind_person_idx.append(pidx)

        cls._cache = cache

        if all_averaged:
            cls._avg_matrix = np.asarray(all_averaged, dtype=np.float32)
        else:
            cls._avg_matrix = np.empty((0, 128), dtype=np.float32)

        if all_ind_normalized:
            cls._ind_matrix = np.asarray(all_ind_normalized, dtype=np.float32)
            cls._ind_person_idx = np.asarray(ind_person_idx, dtype=np.int32)
        else:
            cls._ind_matrix = np.empty((0, 128), dtype=np.float32)
            cls._ind_person_idx = np.empty(0, dtype=np.int32)

    @classmethod
    def warm(cls):
        with cls._lock:
            cls._build()
        logger.info("Embedding cache warmed: %d persons, avg_matrix=%s, ind_matrix=%s",
                     len(cls._cache), cls._avg_matrix.shape, cls._ind_matrix.shape)

    @classmethod
    def refresh(cls):
        with cls._lock:
            cls._build()

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._cache = []
            cls._avg_matrix = None
            cls._ind_matrix = None
            cls._ind_person_idx = []
