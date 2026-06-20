from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any
from uuid import UUID


class ViolationResponse(BaseModel):
    id: UUID
    type: str = Field(..., alias="violation_type")
    plate: Optional[str] = Field(None, alias="plate_number")
    timestamp: datetime
    status: str
    image_url: str

    model_config = {"from_attributes": True, "populate_by_name": True}


class ViolationDetailResponse(BaseModel):
    """Full violation record returned by the detail view modal."""
    id: UUID
    violation_type: str
    vehicle_type: Optional[str] = None
    plate_number: Optional[str] = None
    confidence_score: Optional[float] = None
    status: str
    image_url: str
    plate_image_url: Optional[str] = None
    camera_id: Optional[UUID] = None
    job_id: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    timestamp: datetime

    # Synthetic bounding box data for canvas overlay (populated from mock
    # pipeline or a future /violations/{id}/evidence endpoint).
    bounding_boxes: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class ViolationListMeta(BaseModel):
    total: int
    page: int
    limit: int


class ViolationListResponse(BaseModel):
    data: list[ViolationResponse]
    meta: ViolationListMeta


class ViolationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    notes: Optional[str] = None


class ViolationStatusUpdateResponse(BaseModel):
    id: UUID
    status: str
    updated_at: datetime
