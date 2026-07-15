from .auth_views import register, me
from .upload_views import upload_image, list_images, get_image, delete_image
from .detection_views import detect_faces, get_face_detail, live_detect, live_capture
from .recognition_views import recognize_faces, verify_faces
from .face_management_views import (
    list_known_faces,
    create_known_face,
    get_known_face,
    update_known_face,
    delete_known_face,
    add_face_images,
    delete_face_image,
)
from .report_views import recognition_history, dashboard_stats, update_recognition_log, delete_recognition_log
