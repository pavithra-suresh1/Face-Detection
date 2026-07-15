import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from api.models import UploadedImage
from api.services.mediapipe_service import MediaPipeService

image = UploadedImage.objects.first()

service = MediaPipeService()

img, results = service.detect_faces(image.image.path)

if results.detections:
    print("Faces Detected:", len(results.detections))
else:
    print("No Face Detected")