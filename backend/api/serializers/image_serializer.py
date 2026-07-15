from rest_framework import serializers
from api.models import UploadedImage


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedImage
        fields = ["id", "image", "file_size", "width", "height", "uploaded_at", "processed_image"]
        read_only_fields = ["id", "file_size", "width", "height", "uploaded_at", "processed_image"]


class ImageListSerializer(serializers.ModelSerializer):
    face_count = serializers.SerializerMethodField()

    class Meta:
        model = UploadedImage
        fields = ["id", "image", "file_size", "width", "height", "uploaded_at", "processed_image", "face_count"]

    def get_face_count(self, obj):
        return obj.detected_faces.count()
