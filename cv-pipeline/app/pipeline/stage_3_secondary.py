"""Stage 3 – Secondary Detection (Riders & Accessories).

Real implementation runs a secondary YOLOv8 detector on cropped motorcycle
patches to accurately detect `rider`, `helmet`, and `no_helmet` classes.
Running on crops (640×640) instead of the full frame maximises precision
for small objects that would be lost in full-image down-sampling.
"""

import logging
from typing import Any

import cv2
import numpy as np

from app.config import settings
from app.mock.mock_outputs import MOCK_STAGE_3_SECONDARY
from app.models.yolo import SECONDARY_CLASSES, YOLOModel

logger = logging.getLogger(__name__)

_secondary_yolo: YOLOModel | None = None


def _secondary_model() -> YOLOModel:
    global _secondary_yolo
    if _secondary_yolo is None:
        _secondary_yolo = YOLOModel()
        logger.info("YOLOv8 secondary detector initialised (device=%s)", _secondary_yolo.device)
    return _secondary_yolo


def run_stage_3(data: dict) -> dict:
    """Run secondary detection on motorcycle crop regions.

    Args:
        data: Cumulative pipeline data (includes detections from stage 2).

    Returns:
        Secondary detection dict with rider/helmet results per motorcycle crop.
    """
    # ── Mock path ──────────────────────────────────────────────────────────
    if not settings.USE_REAL_MODELS:
        detections = data.get("stage_2_detection", {})
        if detections.get("skipped"):
            return {"secondary_detections": [], "skipped": True, "reason": "upstream_skip"}
        motorcycles = [d for d in detections.get("detections", []) if d.get("class") == "motorcycle"]
        if not motorcycles:
            return {"secondary_detections": []}
        return MOCK_STAGE_3_SECONDARY

    # ── Real inference path ─────────────────────────────────────────────────
    detections = data.get("stage_2_detection", {})
    if detections.get("skipped"):
        return {"secondary_detections": [], "skipped": True, "reason": "upstream_skip"}

    motorcycles = [d for d in detections.get("detections", []) if d.get("class") == "motorcycle"]
    if not motorcycles:
        return {"secondary_detections": []}

    image_url: str | None = data.get("image_url")
    image_bytes: bytes | None = data.get("image_bytes")

    if image_bytes is None and image_url:
        try:
            import httpx
            resp = httpx.get(image_url, timeout=15)
            resp.raise_for_status()
            image_bytes = resp.content
        except Exception as exc:
            logger.warning("Failed to fetch image for secondary detection: %s", exc)
            return {"secondary_detections": [], "skipped": True, "reason": "fetch_failed"}

    model = _secondary_model()
    secondary_results: list[dict] = []

    for moto_det in motorcycles:
        bbox = moto_det["bbox"]   # xyxy
        x1, y1, x2, y2 = (int(float(v)) for v in bbox)

        # Decode crop from image_bytes if available
        if image_bytes is not None:
            buf = np.frombuffer(image_bytes, dtype=np.uint8)
            full_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if full_bgr is None:
                continue
            crop = full_bgr[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            # Run secondary detection on the crop
            crop_detections = model.detect_on_crop(crop, classes=SECONDARY_CLASSES)

            # Remap class labels to our pipeline's vocabulary
            for det in crop_detections:
                det["class"] = {
                    "person": "rider",
                    "helmet": "helmet",
                    "no_helmet": "no_helmet",
                }.get(det["class"], det["class"])

            # Translate crop-relative bboxes back to full-frame coordinates
            for det in crop_detections:
                rel_bbox = det["bbox"]
                det["bbox"] = [
                    rel_bbox[0] + x1,
                    rel_bbox[1] + y1,
                    rel_bbox[2] + x1,
                    rel_bbox[3] + y1,
                ]

            secondary_results.append({
                "motorcycle_bbox": bbox,
                "detections": crop_detections,
            })

    logger.info("Secondary detection: %d motorcycle crops processed", len(secondary_results))
    return {"secondary_detections": secondary_results}