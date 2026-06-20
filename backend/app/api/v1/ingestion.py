"""Ingestion API — POST /upload.

Receives camera payloads, persists an evidence URL and a job-id row, then
enqueues the CV pipeline task. The endpoint is async (202 Accepted) per the
API_CONTRACTS spec.
"""

import base64
import binascii
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import User, Violation
from app.schemas.ingestion import IngestionRequest, IngestionResponse
from app.services.celery_client import _dispatch_async

logger = logging.getLogger(__name__)
router = APIRouter()


def _decode_image_to_data_uri(image_base64: str) -> str:
    """Validate that the supplied base64 string is decodable; return a data URL.

    In production this URL is replaced by an S3/MinIO upload URL.
    """
    try:
        # Strip any data URL prefix (e.g. "data:image/jpeg;base64,")
        payload = image_base64.split(",", 1)[-1]
        base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image payload: {exc}",
        ) from exc
    return f"data:image/jpeg;base64,{payload}"


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED, response_model=IngestionResponse)
async def upload_image(
    payload: IngestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IngestionResponse:
    """Accept a camera image, persist a violation placeholder, queue the CV job."""
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    image_url = _decode_image_to_data_uri(payload.image_base64)

    # Create the violation placeholder row up front so /violations queries
    # immediately reflect queued jobs.
    violation = Violation(
        job_id=job_id,
        camera_id=payload.camera_id if _is_uuid(payload.camera_id) else None,
        violation_type="pending",  # CV worker replaces this once classified
        confidence_score=None,
        status="pending",
        image_url=image_url,
        timestamp=parse_ts(payload.timestamp),
    )
    db.add(violation)
    # Commit BEFORE enqueueing so the cv-pipeline worker can find the row
    # when it runs. Otherwise a TOCTOU race occurs: the worker may try to
    # SELECT the placeholder before this transaction commits.
    await db.commit()

    logger.info("Ingest job %s (camera=%s)", job_id, payload.camera_id)

    body = {
        "camera_id": payload.camera_id,
        "timestamp": payload.timestamp,
        "image_url": image_url,
        "metadata": payload.metadata or {},
        "violation_id": str(violation.id),
        "job_id": job_id,
    }
    state = _dispatch_async(job_id, body)

    return IngestionResponse(job_id=job_id, status=state)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def parse_ts(value: str) -> __import__("datetime").datetime:  # type: ignore
    from datetime import datetime, timezone

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)
