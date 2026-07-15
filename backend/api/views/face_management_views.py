from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import KnownFace, FaceImage
from api.serializers import KnownFaceSerializer, KnownFaceDetailSerializer, FaceImageSerializer
from api.services import FaceRecognitionService
from api.utils.image_utils import validate_image_file


def _process_face_images(known_face, image_files):
    results = []
    for img_file in image_files:
        try:
            validate_image_file(img_file)
        except ValueError as e:
            continue

        face_img = FaceImage.objects.create(
            known_face=known_face,
            image=img_file,
        )

        embedding = FaceRecognitionService.get_embedding(face_img.image.path)
        if embedding:
            face_img.embedding = embedding
            face_img.save(update_fields=["embedding"])
            results.append(face_img)

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
        return Response(
            {"success": False, "message": "Could not extract face embeddings from any of the uploaded images. Try clearer photos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

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

    processed = _process_face_images(known_face, image_files)
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

    for fi in face.face_images.all():
        try:
            fi.image.delete(save=False)
        except OSError:
            pass
        fi.delete()

    face.delete()
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

    face_image.image.delete(save=False)
    face_image.delete()
    return Response(
        {"success": True, "message": "Face image deleted."},
        status=status.HTTP_200_OK,
    )
