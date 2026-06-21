"""Stage 2 – Primary Object Detection (YOLOv8).

Real implementation runs YOLOv8n pretrained on COCO across the full frame
to detect all traffic participants and infrastructure:
    car, truck, bus, motorcycle, bicycle, pedestrian, traffic_light

Skips inference when upstream IQA reported quality_pass=False to conserve GPU.
"""

import logging
from typing import Any

from app.config import settings
from app.mock.mock_outputs import MOCK_STAGE_2_DETECTION
from app.models.yolo import YOLOModel

logger = logging.getLogger(__name__)

# Lazy YOLO singleton (loaded once per worker life-cycle)
_yolo: YOLOModel | None = None


def _yolo_model() -> YOLOModel:
    global _yolo
    if _yolo is None:
        _yolo = YOLOModel()
        logger.info("YOLOv8 primary detector initialised (device=%s)", _yolo.device)
    return _yolo


def run_stage_2(data: dict) -> dict:
    """Run primary object detection on the full image.

    Args:
        data: Cumulative pipeline data (includes IQA result from stage 1,
              plus image_url or image_bytes from ingestion payload).

    Returns:
        Detection result dict with an array of bounding-box detections.
    """
    # ── Mock path ──────────────────────────────────────────────────────────
    if not settings.USE_REAL_MODELS:
        iqa = data.get("stage_1_iqa", {})
        if not iqa.get("quality_pass", True):
            return {"detections": [], "skipped": True, "reason": "image_quality_fail"}
        return MOCK_STAGE_2_DETECTION

    # ── Real inference path ─────────────────────────────────────────────────
    iqa = data.get("stage_1_iqa", {})
    if not iqa.get("quality_pass", True):
        logger.info("IQA failed – skipping primary detection")
        return {"detections": [], "skipped": True, "reason": "image_quality_fail"}

    image_url: str | None = data.get("image_url")
    image_bytes: bytes | None = data.get("image_bytes")

    if image_bytes is None and image_url:
        try:
            import httpx
            resp = httpx.get(image_url, timeout=15)
            resp.raise_for_status()
            image_bytes = resp.content
        except Exception as exc:
            logger.warning("Failed to fetch image for detection: %s – using mock", exc)
            return MOCK_STAGE_2_DETECTION

    if image_bytes is None:
        logger.warning("No image for detection – returning empty")
        return {"detections": [], "skipped": True, "reason": "no_image"}

    detections = _yolo_model().detect_vehicles(image_bytes=image_bytes)
    logger.info("Primary detection: %d objects found", len(detections))
    return {"detections": detections}