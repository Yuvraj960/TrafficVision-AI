"""Stage 5 – License Plate Detection (LPD).

Real implementation runs a YOLOv8 fine-tuned on license plates to find
the bounding box of every license plate in the frame.  In Phase 8 the
placeholder YOLO (COCO-pretrained) is used; swap LPD_WEIGHTS for a
fine-tuned lpd_yolov8n.pt in production.

LPD is relatively cheap (single forward pass); even non-violation images
run through this stage so the pipeline stays exercised during integration
testing.  In a performance-optimised build, LPD would be gated behind a
Stage-7 pre-check.
"""

import logging
from typing import Any

import cv2
import numpy as np

from app.config import settings
from app.mock.mock_outputs import MOCK_STAGE_5_LPD
from app.models.yolo import LPDModel

logger = logging.getLogger(__name__)

_lpd_model: LPDModel | None = None


def _lpd() -> LPDModel:
    global _lpd_model
    if _lpd_model is None:
        _lpd_model = LPDModel()
        logger.info("LPD model initialised (device=%s)", _lpd_model.device)
    return _lpd_model


def run_stage_5(data: dict) -> dict:
    """Run license-plate detection on the full frame.

    Args:
        data: Cumulative pipeline data (includes tracking from stage 4).

    Returns:
        LPD result dict with license-plate bounding boxes.
    """
    # ── Mock path ──────────────────────────────────────────────────────────
    if not settings.USE_REAL_MODELS:
        tracking = data.get("stage_4_tracking", {})
        if tracking.get("skipped"):
            return {"plates": [], "skipped": True, "reason": "upstream_skip"}
        return MOCK_STAGE_5_LPD

    # ── Real inference path ─────────────────────────────────────────────────
    tracking = data.get("stage_4_tracking", {})
    if tracking.get("skipped"):
        return {"plates": [], "skipped": True, "reason": "upstream_skip"}

    tracks = tracking.get("tracks", [])
    if not tracks:
        return {"plates": []}

    image_url: str | None = data.get("image_url")
    image_bytes: bytes | None = data.get("image_bytes")

    if image_bytes is None and image_url:
        try:
            import httpx
            resp = httpx.get(image_url, timeout=15)
            resp.raise_for_status()
            image_bytes = resp.content
        except Exception as exc:
            logger.warning("Failed to fetch image for LPD: %s — using mock", exc)
            return MOCK_STAGE_5_LPD

    plates: list[dict] = []

    if image_bytes is not None:
        buf = np.frombuffer(image_bytes, dtype=np.uint8)
        full_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if full_bgr is not None:
            detected_plates = _lpd().detect_plates(image_bytes=image_bytes)
            for det in detected_plates:
                # Associate each plate with the closest vehicle track
                best_track = _best_track_for_plate(det["bbox"], tracks)
                plates.append({
                    "vehicle_track_id": best_track,
                    "class": det["class"],
                    "confidence": det["confidence"],
                    "bbox": det["bbox"],
                })

    if not plates:
        logger.info("No plates detected in frame")
    else:
        logger.info("LPD: %d plate(s) found", len(plates))

    return {"plates": plates}


def _best_track_for_plate(plate_bbox: list[float], tracks: list[dict]) -> int | None:
    """Return the track_id whose last centroid is closest (in L2) to the plate."""
    px1, py1, px2, py2 = plate_bbox
    pcx, pcy = (px1 + px2) / 2, (py1 + py2) / 2
    best_id: int | None = None
    best_dist = float("inf")
    for track in tracks:
        trail = track.get("trajectory", [])
        if not trail:
            continue
        txc, tyc = trail[-1]
        dist = ((txc - pcx) ** 2 + (tyc - pcy) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_id = track.get("track_id")
    return best_id