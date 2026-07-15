from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile


def get_image_dimensions(image_path):
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception:
        return None, None


def validate_image_file(uploaded_file):
    valid_prefixes = ["image/"]
    ct = (uploaded_file.content_type or "").lower()
    if not any(ct.startswith(p) for p in valid_prefixes):
        raise ValueError("Unsupported image format. Use JPEG, PNG, or WebP.")
    max_size = 10 * 1024 * 1024
    if uploaded_file.size > max_size:
        raise ValueError("Image too large. Maximum size is 10MB.")
    return True
