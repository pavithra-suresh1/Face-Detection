import numpy as np
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from api.models import DetectedFace, RecognitionLog, UploadedImage


class LiveDetectViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="secret123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("api.views.detection_views.RecognitionService.recognize_face_cached", return_value=(None, 0.0, 0.0))
    @patch("api.views.detection_views.FaceRecognitionService.get_embedding", return_value=[0.1, 0.2, 0.3])
    @patch("api.views.detection_views.EmbeddingCache.get_all", return_value=[])
    @patch("api.views.detection_views.RetinaFaceService.detect_faces", return_value=[{"region": {"x": 0, "y": 0, "w": 20, "h": 20}, "confidence": 0.99}])
    @patch("cv2.imencode", return_value=(True, np.array([1], dtype=np.uint8)))
    @patch("cv2.imread", return_value=np.zeros((40, 40, 3), dtype=np.uint8))
    def test_live_detect_creates_uploaded_image_and_detected_faces(self, *_mocks):
        image_file = SimpleUploadedFile("frame.jpg", b"fake-image", content_type="image/jpeg")

        response = self.client.post("/api/detect-live/", {"image": image_file}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertTrue(UploadedImage.objects.filter(user=self.user).exists())
        self.assertEqual(UploadedImage.objects.filter(user=self.user).count(), 1)
        self.assertEqual(DetectedFace.objects.filter(image__user=self.user).count(), 1)
        self.assertEqual(RecognitionLog.objects.filter(detected_face__image__user=self.user).count(), 1)
