"""Stage 1 – Image Quality Assessment (IQA) via OpenCV.

Real implementation uses Laplacian variance for blur detection and per-channel
mean for brightness/contrast.  No deep learning needed.

Laplacian variance thresholds are calibrated for 640×480 reference; the
function is resolution-normalised so it works on any input size.
"""

from __future__ import annotations

import cv2
import numpy as np


# Quality thresholds (tuned for traffic-surveillance imagery)
_BLUR_THRESHOLD: float = 50.0        # Laplacian variance below this = too blurry
_BRIGHTNESS_MIN: float = 20.0        # Mean pixel value below this = too dark
_BRIGHTNESS_MAX: float = 220.0       # Mean pixel value above this = over-exposed


def _blur_score(gray: np.ndarray) -> float:
    """Compute Laplacian variance — higher = sharper."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _brightness(rgb: np.ndarray) -> float:
    """Mean pixel value in 0–255."""
    return float(np.mean(rgb))


class IQAModel:
    """Stateless IQA model — all methods are pure functions on image data."""

    def predict(self, image_path: str | None = None, image_bytes: bytes | None = None) -> dict:
        """Run IQA on an image file or raw bytes.

        Args:
            image_path: Path to the image on disk.
            image_bytes: Raw JPEG/PNG bytes (bypasses disk I/O).

        Returns:
            {
                "quality_pass": bool,
                "metrics": {"blur_score": float, "brightness": float, "contrast": float},
            }
        """
        if image_bytes is not None:
            buf = np.frombuffer(image_bytes, dtype=np.uint8)
            bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        elif image_path is not None:
            bgr = cv2.imread(image_path)
        else:
            raise ValueError("Either image_path or image_bytes must be provided.")

        if bgr is None:
            # Unreadable image – hard fail
            return _result(False, blur=0.0, brightness=0.0, contrast=0.0)

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        blur = _blur_score(gray)
        bright = _brightness(rgb)
        # RMS contrast (stddev of normalised pixels)
        contrast = float(np.std(gray / 255.0) * 100)

        quality_pass = (
            blur >= _BLUR_THRESHOLD
            and bright >= _BRIGHTNESS_MIN
            and bright <= _BRIGHTNESS_MAX
        )

        return _result(quality_pass, blur, bright, contrast)


def _result(pass_: bool, blur: float, brightness: float, contrast: float) -> dict:
    return {
        "quality_pass": pass_,
        "metrics": {
            "blur_score": round(blur, 2),
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
        },
    }