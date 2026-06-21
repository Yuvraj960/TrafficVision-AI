"""Stage 4 – Multi-Object Tracking (ByteTrack).

Real implementation uses ByteTrack via the supervision library to assign
persistent track IDs across frames and derive per-vehicle trajectory,
speed, and direction vectors.

When only a single frame is available (image-ingestion pipeline) the
tracker returns "identity tracks" (one track per detection), noting that
track continuity requires a video clip input.
"""

import logging
from typing import Any

from app.config import settings
from app.mock.mock_outputs import MOCK_STAGE_4_TRACKING

logger = logging.getLogger(__name__)


def run_stage_4(data: dict) -> dict:
    """Run multi-object tracking on current detections.

    Args:
        data: Cumulative pipeline data (includes detections from stage 2).

    Returns:
        Tracking result dict with track IDs, trajectories, and speed/direction.
    """
    # ── Mock path ──────────────────────────────────────────────────────────
    if not settings.USE_REAL_MODELS:
        detections = data.get("stage_2_detection", {})
        if detections.get("skipped"):
            return {"tracks": [], "skipped": True, "reason": "upstream_skip"}
        return MOCK_STAGE_4_TRACKING

    # ── Real inference path ─────────────────────────────────────────────────
    detections = data.get("stage_2_detection", {})
    if detections.get("skipped"):
        return {"tracks": [], "skipped": True, "reason": "upstream_skip"}

    dets = detections.get("detections", [])
    if not dets:
        return {"tracks": []}

    from app.models import byte_tracker_model

    tracker = byte_tracker_model()

    # Attempt to infer frame size from detections bounding boxes
    frame_w, frame_h = _infer_frame_size(dets)

    tracks = tracker.update(detections=dets, frame_size=(frame_w, frame_h))
    logger.info("Tracking: %d tracks (frame %dx%d)", len(tracks), frame_w, frame_h)

    return {"tracks": tracks}


def _infer_frame_size(detections: list[dict]) -> tuple[int, int]:
    """Heuristic frame size from detection bboxes — max coordinate + padding."""
    max_x, max_y = 0, 0
    for d in detections:
        bbox = d.get("bbox", [])
        if len(bbox) >= 4:
            max_x = max(max_x, float(bbox[2]))
            max_y = max(max_y, float(bbox[3]))
    # Default 1280×720 if no detections
    return (int(max_x * 1.05) or 1280, int(max_y * 1.05) or 720)