import threading
import numpy as np
from api.models import KnownFace, FaceImage


class EmbeddingCache:
    _lock = threading.Lock()
    _cache = None
    _last_known_faces_count = -1
    _last_face_images_count = -1

    @classmethod
    def get_all(cls, force_refresh=False):
        current_kf_count = KnownFace.objects.count()
        current_fi_count = FaceImage.objects.count()
        with cls._lock:
            if (cls._cache is not None and not force_refresh
                    and cls._last_known_faces_count == current_kf_count
                    and cls._last_face_images_count == current_fi_count):
                return cls._cache
            cls._build()
        return cls._cache

    @classmethod
    def _build(cls):
        known_faces = KnownFace.objects.filter(
            face_images__embedding__isnull=False
        ).prefetch_related("face_images").distinct()

        cache = []
        for face in known_faces:
            embeddings = []
            normalized = []
            for img in face.face_images.all():
                if img.embedding:
                    arr = np.asarray(img.embedding, dtype=np.float32)
                    n = np.linalg.norm(arr)
                    embeddings.append(img.embedding)
                    normalized.append((arr / n).tolist() if n > 0 else img.embedding)
            if embeddings:
                cache.append({
                    "id": str(face.id),
                    "name": face.name,
                    "embeddings": embeddings,
                    "normalized": normalized,
                })

        cls._cache = cache
        cls._last_known_faces_count = KnownFace.objects.count()
        cls._last_face_images_count = FaceImage.objects.count()

    @classmethod
    def refresh(cls):
        with cls._lock:
            cls._build()

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._cache = None
            cls._last_known_faces_count = -1
            cls._last_face_images_count = -1
