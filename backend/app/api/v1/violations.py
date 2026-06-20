"""Violation API — list, detail, and status updates.

GET  /violations             paginated list with filters (status, camera_id)
GET  /violations/{id}        full detail record (used by detail modal)
PATCH /violations/{id}/status approve or reject, logs to audit_logs
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import AuditLog, User, Violation
from app.schemas.violation import (
    ViolationDetailResponse,
    ViolationListMeta,
    ViolationListResponse,
    ViolationResponse,
    ViolationStatusUpdate,
    ViolationStatusUpdateResponse,
)

router = APIRouter()


def _synthetic_bboxes(violation_type: str) -> dict[str, Any]:
    """Return mock bounding-box overlays for a given violation type.

    In Phase 8 these are replaced with the actual CV stage outputs stored
    with the violation record (or a separate evidence endpoint).
    """
    if violation_type == "helmet":
        return {
            "vehicles": [{"x": 450, "y": 180, "w": 130, "h": 170, "label": "motorcycle"}],
            "helmets": [],
            "plates": [{"x": 495, "y": 310, "w": 50, "h": 25, "label": "MH 12 AB 1234"}],
            "violations": [
                {"x": 490, "y": 130, "w": 40, "h": 40, "label": "no_helmet"}
            ],
        }
    if violation_type == "triple_riding":
        return {
            "vehicles": [{"x": 450, "y": 180, "w": 130, "h": 170, "label": "motorcycle"}],
            "rider_seats": [
                {"x": 460, "y": 200, "w": 90, "h": 100, "label": "rider 1"},
                {"x": 460, "y": 210, "w": 90, "h": 100, "label": "rider 2"},
                {"x": 460, "y": 220, "w": 90, "h": 100, "label": "rider 3"},
            ],
        }
    if violation_type == "wrong_side":
        return {
            "vehicles": [{"x": 300, "y": 200, "w": 100, "h": 80, "label": "car"}],
            "direction_arrow": {"x": 310, "y": 210, "w": 80, "h": 20, "label": "WRONG WAY"},
        }
    if violation_type == "stop_line":
        return {
            "vehicles": [],
            "stop_line": {"x": 400, "y": 400, "w": 200, "h": 5, "label": "STOP LINE"},
            "intersection": [],
        }
    if violation_type == "overloading":
        return {
            "vehicles": [{"x": 100, "y": 200, "w": 400, "h": 200, "label": "truck"}],
            "cargo": [{"x": 80, "y": 180, "w": 450, "h": 250, "label": "OVERLOADING"}],
        }
    return {}


def _to_response(v: Violation) -> ViolationResponse:
    """Map SQLAlchemy model to paginated-list response shape."""
    return ViolationResponse(
        id=v.id,
        type=v.violation_type,
        plate=v.plate_number,
        timestamp=v.timestamp,
        status=v.status,
        image_url=v.image_url,
    )


def _to_detail(v: Violation) -> ViolationDetailResponse:
    """Map SQLAlchemy model to single-item detail response."""
    return ViolationDetailResponse(
        id=v.id,
        violation_type=v.violation_type,
        vehicle_type=v.vehicle_type,
        plate_number=v.plate_number,
        confidence_score=float(v.confidence_score) if v.confidence_score is not None else None,
        status=v.status,
        image_url=v.image_url,
        plate_image_url=v.plate_image_url,
        camera_id=v.camera_id,
        job_id=v.job_id,
        reviewed_by=v.reviewed_by,
        reviewed_at=v.reviewed_at,
        timestamp=v.timestamp,
        bounding_boxes=_synthetic_bboxes(v.violation_type),
    )


@router.get("/violations", response_model=ViolationListResponse)
async def list_violations(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: pending, approved, rejected",
    ),
    camera_id: Optional[str] = Query(
        None, description="Filter by camera UUID"
    ),
    violation_type: Optional[str] = Query(
        None, description="Filter by type (helmet, triple_riding, etc.)"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ViolationListResponse:
    """Fetch a paginated list of violations with optional filters."""
    stmt = select(Violation)
    count_stmt = select(func.count(Violation.id))

    if status_filter:
        stmt = stmt.where(Violation.status == status_filter)
        count_stmt = count_stmt.where(Violation.status == status_filter)
    if camera_id:
        stmt = stmt.where(Violation.camera_id == camera_id)
        count_stmt = count_stmt.where(Violation.camera_id == camera_id)
    if violation_type:
        stmt = stmt.where(Violation.violation_type == violation_type)
        count_stmt = count_stmt.where(Violation.violation_type == violation_type)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        stmt.order_by(Violation.timestamp.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return ViolationListResponse(
        data=[_to_response(v) for v in rows],
        meta=ViolationListMeta(total=total, page=page, limit=limit),
    )


@router.patch(
    "/violations/{violation_id}/status",
    response_model=ViolationStatusUpdateResponse,
)
async def update_violation_status(
    violation_id: uuid.UUID,
    payload: ViolationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ViolationStatusUpdateResponse:
    """Approve or reject a violation. Logs the action to audit_logs."""
    stmt = await db.execute(select(Violation).where(Violation.id == violation_id))
    violation = stmt.scalar_one_or_none()
    if violation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation {violation_id} not found",
        )

    now = datetime.now(timezone.utc)
    violation.status = payload.status
    violation.reviewed_by = current_user.id
    violation.reviewed_at = now

    audit = AuditLog(
        user_id=current_user.id,
        violation_id=violation.id,
        action=payload.status,
        notes=payload.notes,
    )
    db.add(audit)
    await db.flush()

    return ViolationStatusUpdateResponse(
        id=violation.id,
        status=violation.status,
        updated_at=now,
    )


@router.get("/violations/{violation_id}", response_model=ViolationDetailResponse)
async def get_violation(
    violation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ViolationDetailResponse:
    """Return a single violation record with all fields (used by detail modal)."""
    stmt = await db.execute(select(Violation).where(Violation.id == violation_id))
    violation = stmt.scalar_one_or_none()
    if violation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation {violation_id} not found",
        )
    return _to_detail(violation)
