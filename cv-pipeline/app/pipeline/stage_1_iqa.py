"""Stage 1 – Image Quality Assessment.

Real implementation uses OpenCV to compute Laplacian variance for blur
detection and mean pixel value for brightness/contrast checks.  Returns
a pass/fail decision and diagnostic metrics without deep learning.

Skips downstream GPU-heavy stages on images that fail IQA to save compute.
"""

import logging
from pathlib import Path

from app.config import settings
from app.mock.mock_outputs import MOCK_STAGE_1_IQA

logger = logging.getLogger(__name__)


def run_stage_1(data: dict) -> dict:
    """Run Image Quality Assessment on the source image.

    Args:
        data: Cumulative pipeline data.  Must contain either ``image_url`` or
              ``image_bytes`` from the ingestion payload.

    Returns:
        IQA result dict with quality_pass flag and metric scores.
    """
    if not settings.USE_REAL_MODELS:
        return MOCK_STAGE_1_IQA

    image_url: str | None = data.get("image_url")
    image_bytes: bytes | None = data.get("image_bytes")

    # Try to use image_bytes if available (faster, no HTTP round-trip).
    # Otherwise download from image_url.
    if image_bytes is None and image_url:
        try:
            import httpx
            resp = httpx.get(image_url, timeout=10)
            resp.raise_for_status()
            image_bytes = resp.content
        except Exception as exc:
            logger.warning("Failed to fetch image for IQA: %s — using mock", exc)
            return MOCK_STAGE_1_IQA

    if image_bytes is None:
        # No image available — skip IQA (be permissive)
        logger.info("No image available for IQA — passing with fallback")
        return MOCK_STAGE_1_IQA

    from app.models import iqa_model

    iqa = iqa_model()
    result = iqa.predict(image_bytes=image_bytes)
    logger.info(
        "IQA result: quality_pass=%s  blur=%.1f  brightness=%.1f",
        result["quality_pass"],
        result["metrics"]["blur_score"],
        result["metrics"]["brightness"],
    )
    return result