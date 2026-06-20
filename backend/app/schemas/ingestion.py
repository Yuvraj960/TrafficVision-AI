from pydantic import BaseModel
from typing import Optional


class IngestionRequest(BaseModel):
    camera_id: str
    timestamp: str
    image_base64: str
    metadata: Optional[dict] = None


class IngestionResponse(BaseModel):
    job_id: str
    status: str = "queued"
