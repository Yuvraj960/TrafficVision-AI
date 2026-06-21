"""Celery worker entrypoint for the CV Pipeline service.

Consumes `app.worker.process_image` tasks from the `cv-pipeline` queue,
runs every CV stage in sequence via the orchestrator, and writes the
classified result back to the `violations` table by `job_id`.

The mock phase uses static outputs from `app.mock.mock_outputs`. In the
later phase those are swapped for real PyTorch/ONNX inferences.
"""

import asyncio
import logging
from typing import Any

from celery import Celery

from app.config import settings
from app.db import execute, fetch_one
from app.pipeline.orchestrator import run_pipeline

logger = logging.getLogger(__name__)


# ── Celery app ──────────────────────────────────────────────────────────
app = Celery(
    "cv_pipeline",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="cv-pipeline",
)


# ── DB writeback ────────────────────────────────────────────────────────
async def _persist_pipeline_result(
    job_id: str,
    violation_id: str | None,
) -> str | None:
    """Look up the placeholder row and update it with classified fields.

    Returns:
        The violation row's id, or None if no matching row exists.
    """
    if violation_id:
        row = await fetch_one(
            "SELECT id FROM violations WHERE id::text=$1",
            violation_id,
        )
    else:
        row = await fetch_one(
            "SELECT id FROM violations WHERE job_id=$1 ORDER BY timestamp DESC LIMIT 1",
            job_id,
        )

    if row is None:
        logger.warning("No DB row found for job_id=%s (violation_id=%s)", job_id, violation_id)
        return None
    return str(row["id"])


async def _update_violation_row(
    violations_id: str,
    record: dict[str, Any],
) -> None:
    """Apply the classified record to the existing violation row."""
    vio_type = record.get("violation_type", "unknown")
    confidence = record.get("confidence_score")
    plate = record.get("plate_number")
    vehicle_type = record.get("vehicle_type")
    status = "rejected" if vio_type == "no_violation" else "pending"

    await execute(
        """
        UPDATE violations
           SET violation_type = $1,
               vehicle_type = $2,
               confidence_score = $3,
               plate_number = $4,
               status = $5
         WHERE id::text = $6
        """,
        vio_type,
        vehicle_type,
        confidence,
        plate,
        status,
        violations_id,
    )


async def _persist_and_update(
    job_id: str, violation_id: str | None, record: dict[str, Any]
) -> str | None:
    """Look up, then update in a single event loop so the pool is reused cleanly."""
    vid = await _persist_pipeline_result(job_id, violation_id)
    if vid is not None:
        await _update_violation_row(vid, record)
    return vid


# ── Task ────────────────────────────────────────────────────────────────
@app.task(name="app.worker.process_image", bind=True, max_retries=3, default_retry_delay=10)
def process_image(self, job_id: str, payload: dict | None = None) -> dict:
    """Consume an ingestion event and run the 7-stage CV pipeline.

    Args:
        job_id: Per-ingest unique job identifier (also stored on the row).
        payload: Optional ingestion metadata dict (camera_id, image_url,
                 timestamp, etc.). The backend passes this through.
    """
    payload = payload or {}
    logger.info("Worker received job_id=%s (camera_id=%s)", job_id, payload.get("camera_id"))

    try:
        # Stage 1..7 through orchestrator
        result = run_pipeline(job_id, payload)
        record = result.get("violation_record", {})

        # Persist to DB (single async block reuses the connection pool cleanly)
        violations_id = asyncio.run(
            _persist_and_update(job_id, payload.get("violation_id"), record)
        )
        if violations_id:
            logger.info("job_id=%s -> updated violations.id=%s", job_id, violations_id)

        return {
            "job_id": job_id,
            "violations_id": violations_id,
            "violation_record": record,
        }

    except Exception:
        logger.exception("Pipeline failed for job_id=%s; retrying", job_id)
        raise self.retry(exc=__import__("sys").exc_info()[1])


# ── Worker shutdown hook ────────────────────────────────────────────────
from celery.signals import worker_shutdown  # noqa: E402


@worker_shutdown.connect
def _on_worker_shutdown(**_kwargs):
    # Pools are now scoped per-task, so there is nothing to close on shutdown.
    logger.info("CV pipeline worker shutting down")
