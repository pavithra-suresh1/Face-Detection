from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import UploadedImage
from api.serializers import ImageUploadSerializer, ImageListSerializer
from api.utils.image_utils import get_image_dimensions, validate_image_file


@api_view(["POST"])
def upload_image(request):
    file = request.FILES.get("image")
    if not file:
        return Response({"success": False, "message": "No image provided."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_image_file(file)
    except ValueError as e:
        return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ImageUploadSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        uploaded = serializer.save(user=request.user if request.user.is_authenticated else None)
        width, height = get_image_dimensions(uploaded.image.path)
        uploaded.file_size = uploaded.image.size
        uploaded.width = width
        uploaded.height = height
        uploaded.save(update_fields=["file_size", "width", "height"])

        return Response(
            {"success": True, "message": "Image uploaded successfully.", "data": ImageListSerializer(uploaded).data},
            status=status.HTTP_201_CREATED,
        )

    return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def list_images(request):
    images = UploadedImage.objects.filter(user=request.user)
    page = request.query_params.get("page", 1)
    page_size = 20

    from django.core.paginator import Paginator
    paginator = Paginator(images, page_size)
    page_obj = paginator.get_page(page)

    serializer = ImageListSerializer(page_obj, many=True)
    return Response(
        {
            "success": True,
            "data": serializer.data,
            "total": paginator.count,
            "page": page_obj.number,
            "pages": paginator.num_pages,
        }
    )


@api_view(["GET"])
def get_image(request, pk):
    try:
        image = UploadedImage.objects.get(id=pk, user=request.user)
    except UploadedImage.DoesNotExist:
        return Response({"success": False, "message": "Image not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = ImageListSerializer(image)
    return Response({"success": True, "data": serializer.data})


@api_view(["DELETE"])
def delete_image(request, pk):
    try:
        image = UploadedImage.objects.get(id=pk, user=request.user)
    except UploadedImage.DoesNotExist:
        return Response({"success": False, "message": "Image not found."}, status=status.HTTP_404_NOT_FOUND)

    image.image.delete(save=False)
    if image.processed_image:
        image.processed_image.delete(save=False)
    image.delete()
    return Response({"success": True, "message": "Image deleted."}, status=status.HTTP_200_OK)
