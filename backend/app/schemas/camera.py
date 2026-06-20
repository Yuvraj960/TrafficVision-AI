from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class CameraResponse(BaseModel):
    id: UUID
    name: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    rtsp_url: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CameraCreate(BaseModel):
    name: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    rtsp_url: Optional[str] = None
    status: str = "active"
