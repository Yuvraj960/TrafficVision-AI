"""Inline fallback used when Celery/Redis is unreachable.

Mirrors the data contract of `cv-pipeline/app/pipeline/orchestrator.py` so the
queueing layer can be exercised standalone during development.
"""

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.database import async_session
from app.models import Violation

logger = logging.getLogger(__name__)


async def process_inline(job_id: str, payload: dict[str, Any]) -> None:
    """Apply mock violation rule logic and persist a Violation row."""
    camera_id = payload.get("camera_id")
    image_url = payload.get("image_url", "")
    ts_str = payload.get("timestamp")

    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.now(timezone.utc)
    except Exception:  # noqa: BLE001
        ts = datetime.now(timezone.utc)

    # Mock CV inference: always picks one of the spec'd types with random conf
    violation_type = random.choice(
        ["helmet", "triple_riding", "wrong_side", "stop_line"]
    )
    confidence = round(random.uniform(0.70, 0.95), 4)
    plate_text = f"MH 12 AB {random.randint(1000, 9999)}"

    async with async_session() as session:
        violation = Violation(
            camera_id=camera_id if camera_id else None,
            job_id=job_id,
            violation_type=violation_type,
            vehicle_type="motorcycle",
            plate_number=plate_text,
            confidence_score=confidence,
            status="pending",
            image_url=image_url,
            plate_image_url=None,
            timestamp=ts,
        )
        session.add(violation)
        await session.commit()
        logger.info(
            "Inline-processed job=%s -> violation=%s (%s)",
            job_id,
            violation.id,
            violation_type,
        )
