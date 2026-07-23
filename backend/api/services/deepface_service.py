import os
import cv2
import numpy as np
from deepface import DeepFace
from api.utils.preprocessing import ImagePreprocessor
from api.utils.preprocessing import EmbeddingNormalizer


class DeepFaceService:

    MODEL_NAME = "Facenet"
    DETECTOR = "retinaface"

    @staticmethod
    def _preprocess(image_path):
        image = cv2.imread(image_path)

        if image is None:
            return image_path

        image = ImagePreprocessor.auto_resize_numpy(image)
        image = ImagePreprocessor.clahe_enhance(image)

        denoised = cv2.fastNlMeansDenoisingColored(
            image,
            None,
            10,
            10,
            7,
            21
        )

        temp_path = image_path.replace(
            ".jpg",
            "_enhanced.jpg"
        ).replace(
            ".png",
            "_enhanced.png"
        )

        cv2.imwrite(
            temp_path,
            denoised,
            [cv2.IMWRITE_JPEG_QUALITY, 95]
        )

        return temp_path

    @classmethod
    def analyze_face(cls, image_path):

        temp = None

        try:

            result = DeepFace.analyze(
                img_path=image_path,
                actions=[
                    "age",
                    "gender",
                    "emotion",
                    "race"
                ],
                detector_backend=cls.DETECTOR,
                align=True,
                enforce_detection=True
            )

        except Exception:

            temp = cls._preprocess(image_path)

            try:

                result = DeepFace.analyze(
                    img_path=temp,
                    actions=[
                        "age",
                        "gender",
                        "emotion",
                        "race"
                    ],
                    detector_backend=cls.DETECTOR,
                    align=True,
                    enforce_detection=False
                )

            except Exception:

                if temp and os.path.exists(temp):
                    os.remove(temp)

                return None

        finally:

            if temp and os.path.exists(temp):
                os.remove(temp)

        if not result:
            return None

        data = result[0]

        return {

            "age": int(data["age"]),

            "dominant_gender": data["dominant_gender"],

            "gender_confidence": round(
                float(
                    data["gender"][data["dominant_gender"]]
                ),
                2
            ),

            "dominant_emotion": data["dominant_emotion"],

            "emotion_confidence": round(
                float(
                    data["emotion"][data["dominant_emotion"]]
                ),
                2
            ),

            "emotion_scores": {
                k: round(float(v), 2)
                for k, v in data["emotion"].items()
            },

            "dominant_race": data["dominant_race"],

            "race_confidence": round(
                float(
                    data["race"][data["dominant_race"]]
                ),
                2
            ),

            "face_confidence": round(
                float(
                    data.get("face_confidence", 0)
                ),
                2
            ),

            "region": data["region"]

        }

    @classmethod
    def get_embedding(cls, image_path):

        temp = None

        try:

            embedding = DeepFace.represent(
                img_path=image_path,
                model_name=cls.MODEL_NAME,
                detector_backend=cls.DETECTOR,
                align=True,
                enforce_detection=True
            )

        except Exception:

            temp = cls._preprocess(image_path)

            try:

                embedding = DeepFace.represent(
                    img_path=temp,
                    model_name=cls.MODEL_NAME,
                    detector_backend=cls.DETECTOR,
                    align=True,
                    enforce_detection=False
                )

            except Exception:

                if temp and os.path.exists(temp):
                    os.remove(temp)

                return None

        finally:

            if temp and os.path.exists(temp):
                os.remove(temp)

        if not embedding:
            return None

        vector = np.asarray(
            embedding[0]["embedding"],
            dtype=np.float32
        )

        vector = EmbeddingNormalizer.normalize_l2(vector)

        return vector.tolist()

    @classmethod
    def verify_faces(cls, img1_path, img2_path):

        result = DeepFace.verify(
            img1_path=img1_path,
            img2_path=img2_path,
            model_name=cls.MODEL_NAME,
            detector_backend=cls.DETECTOR,
            align=True,
            enforce_detection=False
        )

        return {

            "verified": result["verified"],

            "distance": round(
                float(result["distance"]),
                4
            ),

            "threshold": float(result["threshold"]),

            "model": result["model"]

        }