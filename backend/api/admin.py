from django.contrib import admin
from .models import UploadedImage, DetectedFace, KnownFace, RecognitionLog


@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "file_size", "uploaded_at"]
    list_filter = ["uploaded_at"]


@admin.register(DetectedFace)
class DetectedFaceAdmin(admin.ModelAdmin):
    list_display = ["id", "image", "face_confidence", "detected_at"]


@admin.register(KnownFace)
class KnownFaceAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "user", "created_at"]


@admin.register(RecognitionLog)
class RecognitionLogAdmin(admin.ModelAdmin):
    list_display = ["id", "detected_face", "matched_face", "is_known", "confidence", "processed_at"]
