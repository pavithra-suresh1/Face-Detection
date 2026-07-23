from django.core.management.base import BaseCommand
from api.models import FaceImage, DetectedFace
from api.utils.preprocessing import EmbeddingNormalizer
from api.services.embedding_cache import EmbeddingCache


class Command(BaseCommand):
    help = "Re-normalize all face embeddings in the database to L2 unit vectors."

    def handle(self, *args, **options):
        normalized_count = 0
        skipped_count = 0

        face_images = FaceImage.objects.filter(embedding__isnull=False)
        self.stdout.write(f"Processing {face_images.count()} FaceImage embeddings...")
        for fi in face_images:
            embedding = fi.embedding
            normed = EmbeddingNormalizer.normalize_l2(embedding)
            if EmbeddingNormalizer.is_normalized(embedding):
                skipped_count += 1
                continue
            fi.embedding = normed.tolist()
            fi.save(update_fields=["embedding"])
            normalized_count += 1

        detected_faces = DetectedFace.objects.filter(embedding__isnull=False)
        self.stdout.write(f"Processing {detected_faces.count()} DetectedFace embeddings...")
        for df in detected_faces:
            embedding = df.embedding
            normed = EmbeddingNormalizer.normalize_l2(embedding)
            if EmbeddingNormalizer.is_normalized(embedding):
                skipped_count += 1
                continue
            df.embedding = normed.tolist()
            df.save(update_fields=["embedding"])
            normalized_count += 1

        EmbeddingCache.refresh()

        self.stdout.write(self.style.SUCCESS(
            f"Done. Normalized: {normalized_count}, Already normalized: {skipped_count}"
        ))
