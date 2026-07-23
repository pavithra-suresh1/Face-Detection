import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import KnownFace, FaceImage
from api.serializers import KnownFaceSerializer, KnownFaceDetailSerializer, FaceImageSerializer
from api.services import FaceRecognitionService
from api.services.retinaface_service import RetinaFaceService
from api.services.embedding_cache import EmbeddingCache
from api.utils.image_utils import validate_image_file
from api.utils.preprocessing import ImagePreprocessor
from api.utils.preprocessing import ImageQualityValidator
from api.utils.preprocessing import FaceValidator
from api.config.thresholds import Thresholds

logger = logging.getLogger(__name__)


def _process_face_images(known_face, image_files):
    results = []
    for img_file in image_files:
        try:
            validate_image_file(img_file)
        except ValueError as e:
            logger.warning("Skipping invalid image file: %s", e)
            continue

        face_img = FaceImage.objects.create(
            known_face=known_face,
            image=img_file,
        )

        ImagePreprocessor.fix_exif_orientation(face_img.image.path)
        ImagePreprocessor.auto_resize(face_img.image.path)

        quality = ImageQualityValidator.validate(face_img.image.path)
        if not quality["valid"]:
            logger.info("Image %s rejected by quality check: %s", img_file.name, [i["type"] for i in quality["issues"]])
            face_img.image.delete(save=False)
            face_img.delete()
            continue

        detected = RetinaFaceService.detect_faces(face_img.image.path)
        face_result = FaceValidator.validate_faces(detected)
        if not face_result["valid"]:
            logger.info("Image %s rejected by face validation: %s", img_file.name, [i["type"] for i in face_result["issues"]])
            face_img.image.delete(save=False)
            face_img.delete()
            continue

        embedding = FaceRecognitionService.get_embedding(face_img.image.path)
        if embedding:
            face_img.embedding = embedding
            face_img.save(update_fields=["embedding"])
            results.append(face_img)
        else:
            logger.warning("Could not extract embedding from %s", img_file.name)

    logger.info("Processed %d/%d images for '%s'", len(results), len(image_files), known_face.name)
    return results


@api_view(["GET"])
def list_known_faces(request):
    faces = KnownFace.objects.filter(user=request.user).prefetch_related("face_images")
    serializer = KnownFaceSerializer(faces, many=True)
    return Response({"success": True, "data": serializer.data})


@api_view(["POST"])
def create_known_face(request):
    name = request.data.get("name")
    email = request.data.get("email", "")
    image_files = request.FILES.getlist("images")

    if not name:
        return Response(
            {"success": False, "message": "Name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not image_files:
        return Response(
            {"success": False, "message": "At least one face image is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(image_files) < Thresholds.REFERENCE_MIN_IMAGES:
        return Response(
            {"success": False, "message": f"Please upload at least {Thresholds.REFERENCE_MIN_IMAGES} reference images for reliable recognition."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(image_files) > Thresholds.REFERENCE_MAX_IMAGES:
        return Response(
            {"success": False, "message": f"Maximum {Thresholds.REFERENCE_MAX_IMAGES} reference images allowed. You uploaded {len(image_files)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if KnownFace.objects.filter(user=request.user, name=name).exists():
        return Response(
            {"success": False, "message": "A face with this name is already registered."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    known_face = KnownFace.objects.create(
        user=request.user,
        name=name,
        email=email,
    )

    processed = _process_face_images(known_face, image_files)

    if not processed:
        known_face.delete()
        logger.warning("Registration failed for '%s': no valid embeddings extracted", name)
        return Response(
            {"success": False, "message": "Could not extract face embeddings from any of the uploaded images. Try clearer photos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    EmbeddingCache.refresh()
    logger.info("Registered '%s' with %d image(s)", name, len(processed))
    return Response(
        {
            "success": True,
            "message": f"Face registered successfully with {len(processed)} image(s).",
            "data": KnownFaceSerializer(known_face).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def add_face_images(request, pk):
    try:
        known_face = KnownFace.objects.get(id=pk, user=request.user)
    except KnownFace.DoesNotExist:
        return Response(
            {"success": False, "message": "Known face not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    image_files = request.FILES.getlist("images")
    if not image_files:
        return Response(
            {"success": False, "message": "At least one image is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    current_count = known_face.face_images.count()
    total_after = current_count + len(image_files)
    if total_after > Thresholds.REFERENCE_MAX_IMAGES:
        allowed = Thresholds.REFERENCE_MAX_IMAGES - current_count
        return Response(
            {"success": False, "message": f"This person already has {current_count} image(s). Maximum is {Thresholds.REFERENCE_MAX_IMAGES}. You can add {allowed} more."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    processed = _process_face_images(known_face, image_files)
    EmbeddingCache.refresh()
    return Response(
        {
            "success": True,
            "message": f"Added {len(processed)} image(s) to {known_face.name}.",
            "data": KnownFaceSerializer(known_face).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def get_known_face(request, pk):
    try:
        face = KnownFace.objects.get(id=pk, user=request.user)
    except KnownFace.DoesNotExist:
        return Response(
            {"success": False, "message": "Known face not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = KnownFaceDetailSerializer(face)
    return Response({"success": True, "data": serializer.data})


@api_view(["PUT"])
def update_known_face(request, pk):
    try:
        face = KnownFace.objects.get(id=pk, user=request.user)
    except KnownFace.DoesNotExist:
        return Response(
            {"success": False, "message": "Known face not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = KnownFaceDetailSerializer(face, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        EmbeddingCache.refresh()
        return Response(
            {"success": True, "data": KnownFaceSerializer(face).data}
        )

    return Response(
        {"success": False, "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["DELETE"])
def delete_known_face(request, pk):
    try:
        face = KnownFace.objects.get(id=pk, user=request.user)
    except KnownFace.DoesNotExist:
        return Response(
            {"success": False, "message": "Known face not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    face_name = face.name

    for fi in face.face_images.all():
        try:
            fi.image.delete(save=False)
        except OSError:
            pass
        fi.delete()

    face.delete()
    EmbeddingCache.refresh()
    logger.info("Deleted known face '%s' (id=%s)", face_name, pk)
    return Response(
        {"success": True, "message": "Known face deleted."},
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
def delete_face_image(request, pk, image_pk):
    try:
        face = KnownFace.objects.get(id=pk, user=request.user)
        face_image = face.face_images.get(id=image_pk)
    except (KnownFace.DoesNotExist, FaceImage.DoesNotExist):
        return Response(
            {"success": False, "message": "Face image not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    current_count = face.face_images.count()
    if current_count <= Thresholds.REFERENCE_MIN_IMAGES:
        return Response(
            {"success": False, "message": f"Cannot delete. A minimum of {Thresholds.REFERENCE_MIN_IMAGES} reference images is required for reliable recognition."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    face_image.image.delete(save=False)
    face_image.delete()
    EmbeddingCache.refresh()
    logger.info("Deleted image %s from '%s'", image_pk, face.name)
    return Response(
        {"success": True, "message": "Face image deleted."},
        status=status.HTTP_200_OK,
    )
