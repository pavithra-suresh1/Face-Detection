import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from api.models import UploadedImage
from deepface import DeepFace

image = UploadedImage.objects.first()

print("Image Path:", image.image.path)

result = DeepFace.analyze(
    img_path=image.image.path,
    actions=["age", "gender", "emotion"],
    enforce_detection=False
)

print(result)
