"""EasyOCR reader for license-plate character recognition.

EasyOCR downloads its model files (~70 MB for english_g2) on first run and
caches them under ~/.easyocr/ or the directory pointed to by ENVIRONMENT.
We initialise lazily so the worker can start without internet access.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)

# We cache the reader as a module-level singleton so we pay the ~3 s
# initialisation cost only once per worker process.
_reader: "easyocr.Reader | None" = None


def build_easyocr_reader(detect_direction: bool = False) -> "easyocr.Reader":
    """Build (and cache) the EasyOCR reader.

    Internet is required on first call to download model files.
    Subsequent calls reuse the cached weights.
    """
    global _reader
    if _reader is None:
        import easyocr

        logger.info("Initialising EasyOCR reader (first run may download weights) ...")
        _reader = easyocr.Reader(
            ["en"],
            gpu=True,          # set False to force CPU
            model_storage_directory=None,  # default ~/.easyocr
            download_enabled=True,
            detection_model_name="DBGRPCNet",
            recognizer_model_name="CRNN",
        )
        logger.info("EasyOCR reader ready")
    return _reader


def read_plate(
    plate_crop: np.ndarray,
    reader: "easyocr.Reader | None" = None,
) -> Tuple[str, float]:
    """Run OCR on a cropped license-plate image.

    Args:
        plate_crop: BGR numpy image (OpenCV format).
        reader: Optional pre-built reader to avoid re-initialising.

    Returns:
        (plate_text, mean_char_confidence)
        Returns ("", 0.0) on failure.
    """
    if reader is None:
        reader = build_easyocr_reader()

    # EasyOCR expects RGB
    rgb = plate_crop[..., ::-1]

    try:
        results = reader.readtext(rgb, batch_size=1, workers=0)
    except Exception as exc:
        logger.warning("OCR inference failed: %s", exc)
        return "", 0.0

    if not results:
        return "", 0.0

    # Aggregate per-character confidences into a single text string
    parts: list[str] = []
    confidences: list[float] = []

    for (bbox, text, confidence) in results:
        # Skip low-confidence reads
        if confidence < 0.3:
            continue
        # Normalise: remove spaces and non-alphanumeric (some models output with spaces)
        cleaned = text.strip().replace(" ", "").upper()
        # Filter characters unlikely to appear on Indian plates (keep alphanumeric + space)
        import re
        cleaned = re.sub(r"[^A-Z0-9 ]", "", cleaned)
        if cleaned:
            parts.append(cleaned)
            confidences.append(confidence)

    if not parts:
        return "", 0.0

    full_text = " ".join(parts)
    mean_conf = float(np.mean(confidences)) if confidences else 0.0
    return full_text, mean_conf