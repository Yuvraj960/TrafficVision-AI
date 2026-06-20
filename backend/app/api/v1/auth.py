"""Authentication endpoints — login issues JWT, /me returns current user info."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    create_access_token,
    get_current_user,
    get_db,
    verify_password,
)
from app.models import User

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: str
    username: str
    role: str


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a JWT for a valid username / password pair."""
    stmt = await db.execute(select(User).where(User.username == form_data.username))
    user = stmt.scalar_one_or_none()
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user))


@router.get("/auth/me", response_model=CurrentUserResponse)
async def read_me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Return the current authenticated user."""
    return CurrentUserResponse(
        id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
    )
