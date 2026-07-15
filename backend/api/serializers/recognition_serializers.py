from rest_framework import serializers
from api.models import KnownFace, FaceImage, RecognitionLog


class FaceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceImage
        fields = ["id", "image", "created_at"]
        read_only_fields = ["id", "created_at"]


class KnownFaceSerializer(serializers.ModelSerializer):
    face_images = FaceImageSerializer(many=True, read_only=True)
    image_count = serializers.SerializerMethodField()

    class Meta:
        model = KnownFace
        fields = ["id", "name", "email", "face_images", "image_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    @staticmethod
    def get_image_count(obj):
        return obj.face_images.count()


class KnownFaceDetailSerializer(serializers.ModelSerializer):
    face_images = FaceImageSerializer(many=True, read_only=True)

    class Meta:
        model = KnownFace
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class RecognitionLogSerializer(serializers.ModelSerializer):
    matched_face_name = serializers.CharField(
        source="matched_face.name", read_only=True, allow_null=True
    )
    matched_face_email = serializers.CharField(
        source="matched_face.email", read_only=True, allow_null=True
    )
    bounding_box = serializers.JSONField(
        source="detected_face.bounding_box", read_only=True
    )

    class Meta:
        model = RecognitionLog
        fields = "__all__"
