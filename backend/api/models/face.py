import uuid
from django.db import models


class DetectedFace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ForeignKey(
        "api.UploadedImage",
        on_delete=models.CASCADE,
        related_name="detected_faces",
    )
    bounding_box = models.JSONField()
    face_confidence = models.FloatField(null=True, blank=True)
    embedding = models.JSONField(null=True, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self):
        return f"Face {self.id} in Image {self.image_id}"
