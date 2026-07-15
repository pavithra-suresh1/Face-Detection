from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import DetectedFace, UploadedImage, RecognitionLog
from api.serializers import RecognitionLogSerializer
from api.services import FaceRecognitionService, RecognitionService


@api_view(["POST"])
def recognize_faces(request):
    image_id = request.data.get("image_id")

    if not image_id:
        return Response(
            {"success": False, "message": "image_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    faces = DetectedFace.objects.filter(image_id=image_id, image__user=request.user)

    if not faces.exists():
        return Response(
            {
                "success": False,
                "message": "No detected faces found. Run detection first.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    results = []
    for face in faces:
        if not face.embedding:
            crop_path = None
            analysis_path = face.image.image.path
            try:
                from api.views.detection_views import _crop_and_save_face
                crop_path = _crop_and_save_face(analysis_path, face.bounding_box)
                if crop_path:
                    analysis_path = crop_path
            except Exception:
                pass

            embedding = FaceRecognitionService.get_embedding(analysis_path)
            if embedding:
                face.embedding = embedding
                face.save(update_fields=["embedding"])

            if crop_path:
                try:
                    import os
                    os.remove(crop_path)
                except Exception:
                    pass

        if face.embedding:
            match, distance, confidence = RecognitionService.recognize_face(face.embedding)
            log = RecognitionLog.objects.create(
                detected_face=face,
                matched_face=match,
                confidence=confidence,
                is_known=match is not None,
            )
            results.append(RecognitionLogSerializer(log).data)

    return Response({"success": True, "recognitions": results, "total": len(results)})


@api_view(["POST"])
def verify_faces(request):
    image_id_1 = request.data.get("image_id_1")
    image_id_2 = request.data.get("image_id_2")

    if not image_id_1 or not image_id_2:
        return Response(
            {"success": False, "message": "Both image_id_1 and image_id_2 are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        img1 = UploadedImage.objects.get(id=image_id_1, user=request.user)
        img2 = UploadedImage.objects.get(id=image_id_2, user=request.user)
    except UploadedImage.DoesNotExist:
        return Response(
            {"success": False, "message": "Image not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    result = RecognitionService.verify_pair(img1.image.path, img2.image.path)
    return Response({"success": True, "verification": result})
