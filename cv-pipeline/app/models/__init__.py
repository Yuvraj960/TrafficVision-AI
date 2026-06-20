"""Computer Vision Models — lazy-loading model registry.

Each loader is a singleton (created on first call, reused thereafter).
This avoids repeatedly loading YOLOv8 / EasyOCR weights, which is slow.

Import from here rather than directly from submodules:
    from app.models import yolo_detector, easyocr_reader, byte_tracker, iqa_model
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy singletons ─────────────────────────────────────────────────────────
_yolo: Any = None
_easyocr: Any = None
_byte_tracker: Any = None


def yolo_detector() -> Any:
    """YOLOv8 primary vehicle detector (COCO-pretrained, used for Stage 2)."""
    global _yolo
    if _yolo is None:
        from app.models.yolo import YOLOModel

        _yolo = YOLOModel()
        logger.info("YOLOv8 primary detector loaded (device=%s)", _yolo.device)
    return _yolo


def secondary_detector() -> Any:
    """Secondary YOLOv8 rider/helmet detector (used for Stage 3)."""
    global _yolo
    if _yolo is None:
        from app.models.yolo import YOLOModel

        _yolo = YOLOModel()
        logger.info("YOLOv8 secondary detector loaded (device=%s)", _yolo.device)
    return _yolo


def lpd_detector() -> Any:
    """YOLOv8 license-plate detector (fine-tuned, used for Stage 5)."""
    from app.models.yolo import LPDModel

    return LPDModel()


def easyocr_reader() -> Any:
    """EasyOCR reader for license-plate text (used for Stage 6)."""
    global _easyocr
    if _easyocr is None:
        from app.models.ocr import build_easyocr_reader

        _easyocr = build_easyocr_reader()
        logger.info("EasyOCR reader loaded")
    return _easyocr


def byte_tracker_model() -> Any:
    """ByteTrack instance for Stage 4 (stateful – call reset() on new video)."""
    global _byte_tracker
    if _byte_tracker is None:
        from app.models.tracker import ByteTrackModel

        _byte_tracker = ByteTrackModel()
        logger.info("ByteTrack model loaded")
    return _byte_tracker


def iqa_model() -> Any:
    """IQA model (stateless — no singleton needed)."""
    from app.models.iqa import IQAModel

    return IQAModel()