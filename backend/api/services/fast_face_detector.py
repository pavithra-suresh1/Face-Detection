import cv2

_face_cascade = None


def _get_cascade():
    global _face_cascade

    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    return _face_cascade


def detect_faces_fast(frame):

    cascade = _get_cascade()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    rects = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(80, 80),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )

    img_h, img_w = frame.shape[:2]

    faces = []

    for (x, y, w, h) in rects:

        # Ignore very small faces
        if w < 80 or h < 80:
            continue

        # Ignore tiny face area
        if w * h < 9000:
            continue

        # Face aspect ratio
        ratio = w / float(h)

        if ratio < 0.70 or ratio > 1.40:
            continue

        # Ignore detections touching image border
        margin = 10

        if (
            x < margin
            or y < margin
            or x + w > img_w - margin
            or y + h > img_h - margin
        ):
            continue

        # Reject very dark detections
        roi = gray[y:y+h, x:x+w]

        if roi.size == 0:
            continue

        if roi.mean() < 35:
            continue

        # Expand face box
        pad_x = int(w * 0.18)
        pad_y = int(h * 0.22)

        nx = max(0, x - pad_x)
        ny = max(0, y - pad_y)

        nw = min(img_w - nx, w + pad_x * 2)
        nh = min(img_h - ny, h + pad_y * 2)

        faces.append({
            "x": int(nx),
            "y": int(ny),
            "w": int(nw),
            "h": int(nh),
        })

    _merge_close_faces(faces)

    return faces


def _merge_close_faces(faces):

    if len(faces) <= 1:
        return

    merged = []
    used = [False] * len(faces)

    for i in range(len(faces)):

        if used[i]:
            continue

        x1 = faces[i]["x"]
        y1 = faces[i]["y"]
        w1 = faces[i]["w"]
        h1 = faces[i]["h"]

        for j in range(i + 1, len(faces)):

            if used[j]:
                continue

            x2 = faces[j]["x"]
            y2 = faces[j]["y"]
            w2 = faces[j]["w"]
            h2 = faces[j]["h"]

            ix1 = max(x1, x2)
            iy1 = max(y1, y2)
            ix2 = min(x1 + w1, x2 + w2)
            iy2 = min(y1 + h1, y2 + h2)

            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)

            area1 = w1 * h1
            area2 = w2 * h2

            overlap = inter / max(1, min(area1, area2))

            if overlap > 0.35:

                nx = min(x1, x2)
                ny = min(y1, y2)

                nw = max(x1 + w1, x2 + w2) - nx
                nh = max(y1 + h1, y2 + h2) - ny

                x1, y1, w1, h1 = nx, ny, nw, nh

                used[j] = True

        merged.append({
            "x": x1,
            "y": y1,
            "w": w1,
            "h": h1,
        })

    faces.clear()
    faces.extend(merged)