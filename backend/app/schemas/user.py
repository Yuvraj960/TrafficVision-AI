from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class UserResponse(BaseModel):
    id: UUID
    username: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(officer|admin)$")


class LoginRequest(BaseModel):
    username: str
    password: str
