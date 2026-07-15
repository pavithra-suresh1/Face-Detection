import cv2
import mediapipe as mp


class MediaPipeService:

    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection

        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=0.5
        )

    def detect_faces(self, image_path):

        image = cv2.imread(image_path)

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        results = self.face_detection.process(rgb_image)

        return image, results