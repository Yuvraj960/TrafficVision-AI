"""Celery client used by the backend API to enqueue pipeline jobs.

The actual worker logic lives in the `cv-pipeline` service. This module exists
in the backend so ingestion endpoints can publish jobs with broker access. If
the broker is unreachable, callers fall back to synchronous in-process mock
processing instead of dropping the image.
"""

import asyncio
import logging
from typing import Any

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

# Producer-style Celery client (does not run a worker)
celery_app = Celery(
    "trafficvision-backend",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_retry_delay=10,
    task_default_max_retries=3,
)


def _dispatch_async(job_id: str, payload: dict[str, Any]) -> str:
    """Enqueue a processing job on the CV pipeline queue.

    Falls back to a placeholder if Redis is unreachable so the API stays
    responsive before the CV worker boots in dev.
    """
    try:
        async_result = celery_app.send_task(
            "app.worker.process_image",
            kwargs={"job_id": job_id, "payload": payload},
            queue="cv-pipeline",
        )
        logger.info("Enqueued job %s (%s)", job_id, async_result.id)
        return "queued"
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Celery enqueue failed for job %s (%s); running inline stub",
            job_id,
            exc,
        )
        # Inline synchronous fallback so the API still records the violation.
        from app.services.fallback_processor import process_inline

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(process_inline(job_id, payload))
        return "inlined"
