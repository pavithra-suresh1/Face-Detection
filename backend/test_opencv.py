import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from api.services.opencv_service import OpenCVService
from api.models import UploadedImage

image = UploadedImage.objects.first()

faces, img = OpenCVService.detect_faces(image.image.path)

print("Faces Detected:", len(faces))