import time


class FaceTracker:
    def __init__(self, iou_threshold=0.35, smoothing=0.40, expire_seconds=1.5):
        self._tracks = {}
        self._next_id = 0
        self._iou_threshold = iou_threshold
        self._smoothing = smoothing
        self._expire = expire_seconds

    def update(self, detections):
        now = time.time()

        for t in self._tracks.values():
            t["matched_this_frame"] = False

        if not self._tracks:
            for d in detections:
                self._create_track(d, now)
            return self._export()

        matched_old = set()
        matched_new = set()
        old_ids = list(self._tracks.keys())
        old_boxes = [self._tracks[tid]["smooth_box"] for tid in old_ids]

        scores = []
        for ni, det in enumerate(detections):
            for oi, old_box in enumerate(old_boxes):
                iou = _iou(det, old_box)
                cp = _center_distance(det, old_box)
                combined = iou * 0.5 + (1.0 - min(cp, 1.0)) * 0.5
                scores.append((combined, ni, oi))
        scores.sort(reverse=True)

        for combined, ni, oi in scores:
            if ni in matched_new or oi in matched_old:
                continue
            if combined < self._iou_threshold:
                break
            self._update_track(old_ids[oi], detections[ni], now)
            matched_old.add(oi)
            matched_new.add(ni)

        for ni, det in enumerate(detections):
            if ni not in matched_new:
                self._create_track(det, now)

        expired = [tid for tid, t in self._tracks.items()
                   if (now - t["last_seen"]) > self._expire]
        for tid in expired:
            del self._tracks[tid]

        self._merge_close_tracks(now)
        return self._export()

    def _merge_close_tracks(self, now):
        ids = list(self._tracks.keys())
        to_delete = set()
        for i in range(len(ids)):
            if ids[i] in to_delete:
                continue
            for j in range(i + 1, len(ids)):
                if ids[j] in to_delete:
                    continue
                box_a = self._tracks[ids[i]]["smooth_box"]
                box_b = self._tracks[ids[j]]["smooth_box"]
                iou_val = _iou(box_a, box_b)
                cd = _center_distance(box_a, box_b)
                if iou_val > 0.3 or cd < 0.4:
                    keep = ids[i] if self._tracks[ids[i]]["last_seen"] >= self._tracks[ids[j]]["last_seen"] else ids[j]
                    drop = ids[j] if keep == ids[i] else ids[i]
                    to_delete.add(drop)
        for tid in to_delete:
            if tid in self._tracks:
                del self._tracks[tid]

    def _create_track(self, det, now):
        tid = self._next_id
        self._next_id += 1
        self._tracks[tid] = {
            "smooth_box": dict(det),
            "label": det.get("label", "Unknown"),
            "is_known": det.get("is_known", False),
            "confidence": det.get("confidence", 0),
            "first_seen": now,
            "last_seen": now,
            "matched_this_frame": True,
        }

    def _update_track(self, tid, det, now):
        t = self._tracks[tid]
        t["last_seen"] = now
        t["matched_this_frame"] = True
        a = self._smoothing
        sb, rb = t["smooth_box"], det
        sb["x"] = int(sb["x"] * (1 - a) + rb["x"] * a)
        sb["y"] = int(sb["y"] * (1 - a) + rb["y"] * a)
        sb["w"] = int(sb["w"] * (1 - a) + rb["w"] * a)
        sb["h"] = int(sb["h"] * (1 - a) + rb["h"] * a)
        if det.get("label") and det["label"] != "Unknown":
            t["label"] = det["label"]
            t["is_known"] = det.get("is_known", False)
            t["confidence"] = det.get("confidence", 0)

    def _export(self):
        out = []
        for tid, t in self._tracks.items():
            if not t["matched_this_frame"]:
                continue
            out.append({
                "track_id": tid,
                "region": dict(t["smooth_box"]),
                "label": t["label"],
                "is_known": t["is_known"],
                "confidence": t["confidence"],
            })
        return out


def _iou(a, b):
    ix1 = max(a["x"], b["x"])
    iy1 = max(a["y"], b["y"])
    ix2 = min(a["x"] + a["w"], b["x"] + b["w"])
    iy2 = min(a["y"] + a["h"], b["y"] + b["h"])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0


def _center_distance(a, b):
    acx, acy = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
    bcx, bcy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    diag = (a["w"] ** 2 + a["h"] ** 2) ** 0.5 or 1
    return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5 / diag
