from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    register,
    me,
    upload_image,
    list_images,
    get_image,
    delete_image,
    detect_faces,
    get_face_detail,
    live_detect,
    live_capture,
    recognize_faces,
    verify_faces,
    list_known_faces,
    create_known_face,
    get_known_face,
    update_known_face,
    delete_known_face,
    add_face_images,
    delete_face_image,
    recognition_history,
    dashboard_stats,
    update_recognition_log,
    delete_recognition_log,
)

urlpatterns = [
    # Auth
    path("auth/register/", register),
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", me),
    # Upload
    path("upload/", upload_image),
    path("uploads/", list_images),
    path("uploads/<uuid:pk>/", get_image),
    path("uploads/<uuid:pk>/delete/", delete_image),
    # Detection
    path("detect/", detect_faces),
    path("detect-live/", live_detect),
    path("capture/", live_capture, name="live_capture"),
    path("faces/<uuid:pk>/", get_face_detail),
    # Recognition
    path("recognize/", recognize_faces),
    path("verify/", verify_faces),
    # Known Faces
    path("known-faces/", list_known_faces),
    path("known-faces/create/", create_known_face),
    path("known-faces/<uuid:pk>/", get_known_face),
    path("known-faces/<uuid:pk>/update/", update_known_face),
    path("known-faces/<uuid:pk>/delete/", delete_known_face),
    path("known-faces/<uuid:pk>/images/", add_face_images),
    path("known-faces/<uuid:pk>/images/<uuid:image_pk>/", delete_face_image),
    # Reports
    path("history/", recognition_history),
    path("history/<uuid:pk>/update/", update_recognition_log),
    path("history/<uuid:pk>/delete/", delete_recognition_log),
    path("stats/", dashboard_stats),
]
