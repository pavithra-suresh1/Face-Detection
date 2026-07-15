from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        "success": True,
        "message": "Face Detection API is running successfully.",
        "version": "1.0.0",
    })
