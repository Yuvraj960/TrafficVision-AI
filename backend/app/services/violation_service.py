"""
Violation service layer.

Encapsulates business logic for violation retrieval, status updates,
and audit trail creation. Currently a skeleton -- will be wired to
the database once full CRUD operations are implemented.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ViolationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_violations(
        self,
        status: Optional[str] = None,
        camera_id: Optional[UUID] = None,
        page: int = 1,
        limit: int = 50,
    ):
        # TODO: implement with real DB queries
        raise NotImplementedError

    async def update_status(
        self,
        violation_id: UUID,
        new_status: str,
        reviewer_id: UUID,
        notes: Optional[str] = None,
    ):
        # TODO: implement with real DB queries + audit log creation
        raise NotImplementedError
