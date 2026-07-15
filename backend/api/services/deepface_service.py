import os
import cv2
import numpy as np
from deepface import DeepFace


class DeepFaceService:

    MODEL_NAME = "Facenet"
    DETECTOR = "retinaface"

    @staticmethod
    def _preprocess(image_path):
        image = cv2.imread(image_path)

        if image is None:
            return image_path

        h, w = image.shape[:2]

        if max(h, w) > 1000:
            scale = 1000 / max(h, w)
            image = cv2.resize(
                image,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_AREA
            )

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        l = clahe.apply(l)

        enhanced = cv2.merge((l, a, b))
        enhanced = cv2.cvtColor(
            enhanced,
            cv2.COLOR_LAB2BGR
        )

        denoised = cv2.fastNlMeansDenoisingColored(
            enhanced,
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

        norm = np.linalg.norm(vector)

        if norm > 0:
            vector = vector / norm

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