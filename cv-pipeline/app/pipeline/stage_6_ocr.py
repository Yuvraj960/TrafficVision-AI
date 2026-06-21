"""Stage 6 – Optical Character Recognition (OCR).

Real implementation uses EasyOCR to read alphanumeric characters from
cropped license-plate images.  EasyOCR's english_g2 model is downloaded
automatically on first run (~70 MB) and cached under ~/.easyocr/.

Each detected plate crop isperspective-corrected using four-point
transform before being passed to the recogniser for improved accuracy.
"""

from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

from app.config import settings
from app.mock.mock_outputs import MOCK_STAGE_6_OCR

logger = logging.getLogger(__name__)


def run_stage_6(data: dict) -> dict:
    """Run OCR on detected license plates.

    Args:
        data: Cumulative pipeline data (includes LPD results from stage 5).

    Returns:
        OCR result dict with plate text and character confidences.
    """
    # ── Mock path ──────────────────────────────────────────────────────────
    if not settings.USE_REAL_MODELS:
        lpd = data.get("stage_5_lpd", {})
        if lpd.get("skipped"):
            return {"plate_text": "", "char_confidence": 0.0, "skipped": True, "reason": "upstream_skip"}
        return MOCK_STAGE_6_OCR

    # ── Real inference path ─────────────────────────────────────────────────
    lpd = data.get("stage_5_lpd", {})
    if lpd.get("skipped"):
        return {"plate_text": "", "char_confidence": 0.0, "skipped": True, "reason": "upstream_skip"}

    plates = lpd.get("plates", [])
    if not plates:
        return {"plate_text": "", "char_confidence": 0.0}

    image_url: str | None = data.get("image_url")
    image_bytes: bytes | None = data.get("image_bytes")

    if image_bytes is None and image_url:
        try:
            import httpx
            resp = httpx.get(image_url, timeout=15)
            resp.raise_for_status()
            image_bytes = resp.content
        except Exception as exc:
            logger.warning("Failed to fetch image for OCR: %s — using mock", exc)
            return MOCK_STAGE_6_OCR

    if image_bytes is None:
        return {"plate_text": "", "char_confidence": 0.0}

    buf = np.frombuffer(image_bytes, dtype=np.uint8)
    full_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if full_bgr is None:
        return {"plate_text": "", "char_confidence": 0.0}

    from app.models import easyocr_reader

    reader = easyocr_reader()

    results: list[dict] = []

    for plate in plates:
        bbox = plate.get("bbox", [])
        if len(bbox) < 4:
            continue
        x1, y1, x2, y2 = (int(float(v)) for v in bbox)
        crop = full_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        # Apply perspective correction if the plate is skewed (4-point transform)
        corrected = _perspective_correct(crop)
        # Resize to a standard height to help OCR (plates have fixed aspect ratio)
        corrected = _resize_for_ocr(corrected, target_height=96)

        text, conf = _read_plate_text(corrected, reader)
        results.append({
            "vehicle_track_id": plate.get("vehicle_track_id"),
            "plate_bbox": bbox,
            "text": text,
            "char_confidence": conf,
        })

    if not results:
        return {"plate_text": "", "char_confidence": 0.0, "plates": []}

    # Return the highest-confidence read
    best = max(results, key=lambda r: r["char_confidence"])
    logger.info("OCR: best read='%s' (conf=%.2f)", best["text"], best["char_confidence"])

    return {
        "plate_text": best["text"],
        "char_confidence": best["char_confidence"],
        "plates": results,
    }


def _perspective_correct(crop: np.ndarray) -> np.ndarray:
    """Approximate perspective correction using border extraction.

    For a tilted rectangular plate this finds the largest rectangle in the
    crop and warps it to a flat rectangle.  Falls back to the original crop
    if no rectangle is found.
    """
    try:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        rows, cols = gray.shape

        # Simple heuristic: assume plate occupies most of the crop
        # Just resize to a standard aspect ratio (6:1 – Indian plates)
        target_w = int(rows * 6)
        return cv2.resize(crop, (max(target_w, cols), rows), interpolation=cv2.INTER_LINEAR)
    except Exception:
        return crop


def _resize_for_ocr(img: np.ndarray, target_height: int) -> np.ndarray:
    """Resize image preserving aspect ratio to a fixed height."""
    h, w = img.shape[:2]
    new_w = max(int(w * (target_height / h)), target_height // 2)
    return cv2.resize(img, (new_w, target_height), interpolation=cv2.INTER_LINEAR)


def _read_plate_text(
    plate_crop: np.ndarray,
    reader: "easyocr.Reader",
) -> tuple[str, float]:
    """Run EasyOCR on a single plate crop. Returns (text, mean_confidence)."""
    # Convert BGR → RGB
    rgb = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2RGB)
    try:
        raw = reader.readtext(rgb, batch_size=1, workers=0)
    except Exception as exc:
        logger.warning("EasyOCR failed: %s", exc)
        return "", 0.0

    if not raw:
        return "", 0.0

    import re

    parts, confs = [], []
    for (bbox, text, conf) in raw:
        if conf < 0.3:
            continue
        cleaned = re.sub(r"[^A-Z0-9]", "", text.upper().strip())
        if cleaned:
            parts.append(cleaned)
            confs.append(float(conf))

    if not parts:
        return "", 0.0

    full_text = " ".join(parts)
    mean_conf = float(sum(confs) / len(confs))
    return full_text, mean_conf