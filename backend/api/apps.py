import logging
import threading
from django.apps import AppConfig

logger = logging.getLogger(__name__)


def _warm_models():
    try:
        import numpy as np
        from deepface import DeepFace
        dummy = np.zeros((160, 160, 3), dtype=np.uint8)
        for backend in ("mtcnn", "opencv"):
            try:
                DeepFace.represent(
                    img_path=dummy,
                    model_name="Facenet",
                    detector_backend=backend,
                    enforce_detection=False,
                )
                logger.info("DeepFace Facenet + %s model pre-warmed", backend)
            except Exception as e:
                logger.warning("DeepFace %s pre-warm failed: %s", backend, e)
    except Exception as e:
        logger.warning("Model pre-warm failed: %s", e)


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        from api.services.embedding_cache import EmbeddingCache
        EmbeddingCache.warm()

        threading.Thread(target=_warm_models, daemon=True).start()
