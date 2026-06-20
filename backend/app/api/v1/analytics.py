"""Analytics API — aggregated metrics for the dashboard."""

from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import User, Violation
from app.schemas.analytics import AnalyticsSummary

router = APIRouter()


def _to_dt(d: date) -> datetime:
    """Date → start-of-day UTC datetime."""
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    date_from: Optional[date] = Query(None, description="Start date for the range (inclusive)"),
    date_to: Optional[date] = Query(None, description="End date for the range (exclusive)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummary:
    """Return summary analytics for violations within an optional date range.

    Excludes ``pending`` placeholder rows (created from /upload before the CV
    worker completes) so dashboard counts reflect only fully classified cases.
    """
    stmt = select(
        Violation.violation_type, func.count(Violation.id)
    ).where(Violation.violation_type != "pending").group_by(Violation.violation_type)

    if date_from:
        stmt = stmt.where(Violation.timestamp >= _to_dt(date_from))
    if date_to:
        stmt = stmt.where(Violation.timestamp < _to_dt(date_to))

    rows = (await db.execute(stmt)).all()

    by_type: dict[str, int] = {vtype: count for vtype, count in rows}
    total = sum(by_type.values())
    return AnalyticsSummary(total_violations=total, by_type=by_type)
