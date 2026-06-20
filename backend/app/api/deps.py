"""Authentication and authorization dependencies.

Implements JWT-based auth (per API_CONTRACTS). Login endpoint issues tokens;
protected endpoints verify them via the `get_current_user` dependency.
"""

from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models import User

# Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_TIE_MINUTES = 30

# Token issuance / validation entry points
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


# ── Database dependency ──────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Password helpers ─────────────────────────────────────────────────────
def _truncate(plaintext: str) -> bytes:
    """bcrypt 72-byte limit."""
    return plaintext.encode("utf-8")[:72]


def verify_password(plaintext: str, hashed: str) -> bool:
    return _bcrypt.checkpw(_truncate(plaintext), hashed.encode("utf-8"))


def hash_password(plaintext: str) -> str:
    return _bcrypt.hashpw(_truncate(plaintext), _bcrypt.gensalt(rounds=12)).decode("utf-8")


# ── JWT helpers ──────────────────────────────────────────────────────────
class TokenPayload(BaseModel):
    sub: str  # user UUID
    role: str
    exp: int


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TIE_MINUTES)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**decoded)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── Current-user dependency ──────────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    stmt = await db.execute(select(User).where(User.id == payload.sub))
    user = stmt.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Restrict an endpoint to admin-role users only."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
