import cv2
import os
import uuid


class OpenCVService:

    @staticmethod
    def draw_face_boxes(image_path, faces_data):
        image = cv2.imread(image_path)
        if image is None:
            raise Exception("Unable to read image.")

        for face in faces_data:
            region = face.get("region", face.get("bounding_box"))
            if not region:
                continue
            x = int(region["x"])
            y = int(region["y"])
            w = int(region["w"])
            h = int(region["h"])

            is_known = face.get("is_known")
            if is_known is True:
                color = (0, 255, 0)
            elif is_known is False:
                color = (0, 165, 255)
            else:
                color = (0, 255, 0)

            cv2.rectangle(image, (x, y), (x + w, y + h), color, 3)

            label = face.get("label", "")
            if label:
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                label_bg_y1 = max(0, y - th - 10)
                cv2.rectangle(image, (x, label_bg_y1), (x + tw + 10, y), color, -1)
                cv2.putText(
                    image,
                    label,
                    (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                )

        processed_folder = os.path.join("media", "processed")
        os.makedirs(processed_folder, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.jpg"
        output_path = os.path.join(processed_folder, filename)

        success = cv2.imwrite(output_path, image)
        if not success:
            raise Exception("Failed to save processed image.")

        return f"processed/{filename}"
