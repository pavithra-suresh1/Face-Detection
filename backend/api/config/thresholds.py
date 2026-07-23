import json
import os


_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "thresholds.json")

_SECTION_MAP = {
    "FACE_DETECT_CONFIDENCE":       ("face_detection",   "confidence"),
    "FACE_MIN_SIZE_PX":             ("face_detection",   "min_size_px"),
    "SIMILARITY_THRESHOLD":         ("recognition",      "similarity_threshold"),
    "CONFIDENCE_THRESHOLD":         ("recognition",      "confidence_threshold"),
    "LIVE_MATCH_MARGIN":            ("recognition",      "live_match_margin"),
    "MATCH_MIN_IMAGES_FOR_AVERAGED":("recognition",      "min_images_for_averaged"),
    "MATCH_INDIVIDUAL_TOLERANCE":   ("recognition",      "individual_tolerance"),
    "MATCH_MIN_VERIFIED_IMAGES":    ("recognition",      "min_verified_images"),
    "RECOGNITION_FRAME_INTERVAL":   ("live_performance",  "recognition_frame_interval"),
    "RECOGNITION_CACHE_TTL":        ("live_performance",  "recognition_cache_ttl"),
    "MAX_RECOGNITION_RETRIES":      ("live_performance",  "max_recognition_retries"),
    "CHECKING_TIMEOUT_FRAMES":      ("live_performance",  "checking_timeout_frames"),
    "EMBEDDING_DETECTOR_BACKEND":   ("live_performance",  "embedding_detector_backend"),
    "TRACK_EXPIRE_SECONDS":         ("tracking",         "expire_seconds"),
    "TRACK_MATCH_SCORE":            ("tracking",         "match_score"),
    "TRACK_SMOOTHING":              ("tracking",         "smoothing"),
    "TRACK_IOU_RATIO":              ("tracking",         "iou_ratio"),
    "TRACK_CENTER_RATIO":           ("tracking",         "center_ratio"),
    "FRONTAL_ASPECT_MIN":           ("frontal_face",     "aspect_min"),
    "FRONTAL_ASPECT_MAX":           ("frontal_face",     "aspect_max"),
    "RETINAFACE_MIN_CONFIDENCE":    ("retinaface",       "min_confidence"),
    "CLAHE_CLIP_LIMIT":             ("clahe",            "clip_limit"),
    "CLAHE_TILE_SIZE":              ("clahe",            "tile_size"),
    "CLAHE_MAX_DIMENSION":          ("clahe",            "max_dimension"),
    "PREPROCESS_MAX_DIMENSION":     ("preprocessing",    "max_dimension"),
    "QUALITY_BLUR_THRESHOLD":       ("image_quality",    "blur_threshold"),
    "QUALITY_DARK_THRESHOLD":       ("image_quality",    "dark_threshold"),
    "QUALITY_BRIGHT_THRESHOLD":     ("image_quality",    "bright_threshold"),
    "QUALITY_MIN_RESOLUTION":       ("image_quality",    "min_resolution"),
    "FACE_VALIDATION_MIN_SIZE":     ("face_validation",  "min_size"),
    "FACE_VALIDATION_MIN_CONFIDENCE":("face_validation", "min_confidence"),
    "REFERENCE_MIN_IMAGES":         ("reference_images", "min_count"),
    "REFERENCE_MAX_IMAGES":         ("reference_images", "max_count"),
    "PREPROCESS_DARK_THRESHOLD":    ("preprocessing_enhancement", "dark_brightness_threshold"),
    "PREPROCESS_DARK_SOFT":         ("preprocessing_enhancement", "dark_brightness_soft_threshold"),
    "PREPROCESS_BRIGHT_THRESHOLD":  ("preprocessing_enhancement", "bright_brightness_threshold"),
    "PREPROCESS_BRIGHT_SOFT":       ("preprocessing_enhancement", "bright_brightness_soft_threshold"),
    "PREPROCESS_DARK_GAMMA":        ("preprocessing_enhancement", "dark_gamma"),
    "PREPROCESS_DARK_GAMMA_SOFT":   ("preprocessing_enhancement", "dark_gamma_soft"),
    "PREPROCESS_BRIGHT_GAMMA":      ("preprocessing_enhancement", "bright_gamma"),
    "PREPROCESS_BRIGHT_GAMMA_SOFT": ("preprocessing_enhancement", "bright_gamma_soft"),
    "PREPROCESS_BACKLIT_GAMMA":     ("preprocessing_enhancement", "backlit_gamma"),
    "PREPROCESS_SHADOWED_GAMMA":    ("preprocessing_enhancement", "shadowed_gamma"),
    "PREPROCESS_BACKLIT_DARK_RATIO":("preprocessing_enhancement", "backlit_dark_ratio"),
    "PREPROCESS_BACKLIT_BRIGHT_RATIO":("preprocessing_enhancement","backlit_bright_ratio"),
    "PREPROCESS_SHADOWED_DARK_RATIO":("preprocessing_enhancement","shadowed_dark_ratio"),
    "PREPROCESS_LOW_STD":           ("preprocessing_enhancement", "low_std_threshold"),
    "PREPROCESS_LIVE_DARK":         ("preprocessing_enhancement", "live_dark_threshold"),
    "PREPROCESS_LIVE_BRIGHT":       ("preprocessing_enhancement", "live_bright_threshold"),
}


class _ThresholdsMeta(type):
    _config = None

    def _load(cls):
        with open(_CONFIG_PATH, "r") as f:
            cls._config = json.load(f)

    def __getattr__(cls, name):
        if cls._config is None:
            cls._load()
        if name not in _SECTION_MAP:
            raise AttributeError(f"Unknown threshold: {name}")
        section, key = _SECTION_MAP[name]
        try:
            value = cls._config[section][key]
        except KeyError:
            raise AttributeError(f"Missing threshold in config: {section}.{key}")
        if key == "tile_size":
            return tuple(value)
        return value


class Thresholds(metaclass=_ThresholdsMeta):

    @classmethod
    def reload(cls):
        with open(_CONFIG_PATH, "r") as f:
            _ThresholdsMeta._config = json.load(f)
