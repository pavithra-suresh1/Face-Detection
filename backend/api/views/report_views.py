from django.utils import timezone
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import UploadedImage, DetectedFace, RecognitionLog, KnownFace
from api.serializers import RecognitionLogSerializer


@api_view(["GET"])
def recognition_history(request):
    logs = RecognitionLog.objects.filter(
        detected_face__image__user=request.user
    ).select_related("detected_face", "matched_face")

    page = int(request.query_params.get("page", 1))
    page_size = 20
    paginator = Paginator(logs, page_size)
    page_obj = paginator.get_page(page)

    data = []
    for log in page_obj:
        data.append(
            {
                "id": log.id,
                "is_known": log.is_known,
                "confidence": log.confidence,
                "matched_name": log.matched_face.name if log.matched_face else None,
                "matched_email": log.matched_face.email if log.matched_face else None,
                "image_id": str(log.detected_face.image_id),
                "bounding_box": log.detected_face.bounding_box,
                "processed_at": log.processed_at.isoformat(),
            }
        )

    return Response(
        {
            "success": True,
            "data": data,
            "total": paginator.count,
            "page": page_obj.number,
            "pages": paginator.num_pages,
        }
    )


@api_view(["GET"])
def dashboard_stats(request):
    user = request.user
    today = timezone.now().date()

    total_images = UploadedImage.objects.filter(user=user).count()
    total_faces = DetectedFace.objects.filter(image__user=user).count()
    known_faces_count = KnownFace.objects.filter(user=user).count()
    total_recognitions = RecognitionLog.objects.filter(
        detected_face__image__user=user
    ).count()
    known_matches = RecognitionLog.objects.filter(
        detected_face__image__user=user, is_known=True
    ).count()
    unknown_matches = total_recognitions - known_matches

    today_detections = DetectedFace.objects.filter(
        image__user=user, detected_at__date=today
    ).count()
    today_recognitions = RecognitionLog.objects.filter(
        detected_face__image__user=user, processed_at__date=today
    ).count()

    recent_activity = []
    recent_logs = (
        RecognitionLog.objects.filter(detected_face__image__user=user)
        .select_related("detected_face", "matched_face")
        .order_by("-processed_at")[:10]
    )
    for log in recent_logs:
        recent_activity.append(
            {
                "id": log.id,
                "type": "known" if log.is_known else "unknown",
                "name": log.matched_face.name if log.matched_face else "Unknown Person",
                "confidence": log.confidence,
                "time": log.processed_at.isoformat(),
            }
        )

    return Response(
        {
            "success": True,
            "data": {
                "total_images": total_images,
                "total_faces": total_faces,
                "known_faces": known_faces_count,
                "total_recognitions": total_recognitions,
                "known_matches": known_matches,
                "unknown_matches": unknown_matches,
                "today_detections": today_detections,
                "today_recognitions": today_recognitions,
                "recent_activity": recent_activity,
            },
        }
    )


@api_view(["PUT"])
def update_recognition_log(request, pk):
    try:
        log = RecognitionLog.objects.get(id=pk, detected_face__image__user=request.user)
    except RecognitionLog.DoesNotExist:
        return Response(
            {"success": False, "message": "Recognition log not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = RecognitionLogSerializer(log, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({"success": True, "data": serializer.data})
    return Response(
        {"success": False, "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["DELETE"])
def delete_recognition_log(request, pk):
    try:
        log = RecognitionLog.objects.get(id=pk, detected_face__image__user=request.user)
    except RecognitionLog.DoesNotExist:
        return Response(
            {"success": False, "message": "Recognition log not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    log.delete()
    return Response({"success": True, "message": "Recognition log deleted."})
