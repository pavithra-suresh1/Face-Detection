import uuid
from django.db import models


class KnownFace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="known_faces",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["user", "name"]]

    def __str__(self):
        return self.name


class FaceImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    known_face = models.ForeignKey(
        "api.KnownFace",
        on_delete=models.CASCADE,
        related_name="face_images",
    )
    image = models.ImageField(upload_to="known_faces/")
    embedding = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Image for {self.known_face.name}"


class RecognitionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    detected_face = models.ForeignKey(
        "api.DetectedFace",
        on_delete=models.CASCADE,
        related_name="recognition_logs",
    )
    matched_face = models.ForeignKey(
        "api.KnownFace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recognition_logs",
    )
    confidence = models.FloatField(null=True, blank=True)
    is_known = models.BooleanField(default=False)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self):
        return f"{'Known' if self.is_known else 'Unknown'} - {self.matched_face or 'No match'}"
