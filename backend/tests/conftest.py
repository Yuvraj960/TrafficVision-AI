"""Backend test suite — pytest configuration and fixtures.

Uses the same PostgreSQL instance as dev but a separate database (`test_trafficvision`).
Run with:  pytest backend/tests/ -v

Environment variables used in tests:
    TEST_DATABASE_URL  — full asyncpg DSN for the test database.
                         If not set, defaults to localhost.
    SKIP_CELERY        — if set, Celery dispatch is stubbed out in ingestion tests.
"""

import logging
import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Logging ────────────────────────────────────────────────────────────────────
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ── Database URL ──────────────────────────────────────────────────────────────
# Tests use a dedicated 'test_trafficvision' database to avoid polluting dev data.
_TEST_DB: str = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://trafficvision:devpassword@localhost:5432/test_trafficvision",
)

# ── Schema bootstrap ──────────────────────────────────────────────────────────
# Imports must happen after database URL is determined so models use the right URL.
import asyncio
from app.models.base import Base
from app.models import AuditLog, Camera, User, Violation  # noqa: F401 — registers tables


@pytest.fixture(scope="session")
def event_loop():
    """One event loop for the entire test session to avoid engine-per-loop cost."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def _test_engine():
    """Create (or recreate) the test database schema once per test session."""
    # Bootstrap the test database if it doesn't exist.
    # Connect to the default 'postgres' DB to run CREATE DATABASE.
    bootstrap_url = _TEST_DB.rsplit("/", 1)[0] + "/postgres"
    bootstrap_engine = create_async_engine(bootstrap_url, isolation_level="AUTOCOMMIT")

    try:
        async with bootstrap_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname='test_trafficvision'")
            )
            exists = result.scalar() == 1
    except Exception:
        exists = False
    finally:
        await bootstrap_engine.dispose()

    if not exists:
        async with bootstrap_engine.connect() as conn:
            await conn.execute(text("CREATE DATABASE test_trafficvision"))
        await bootstrap_engine.dispose()

    # Now connect to the test DB and run migrations.
    engine = create_async_engine(_TEST_DB, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(_test_engine):
    """Per-session AsyncSessionFactory shared across all test sessions."""
    factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)
    return factory


# ── DB session per test ────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def db(session_factory: async_sessionmaker[AsyncSession]):
    """Each test gets its own committed transaction-session; rolls back automatically."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Authenticated test client ─────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncClient:
    """Fully-wired AsyncClient pointing at the FastAPI app.

    The app's `get_db` dependency is overridden to use `session_factory` so each
    test sees its own transactional session.
    """
    from app.api.deps import get_db
    from app.main import app

    # Override the DB dependency to use the test session factory
    app.dependency_overrides[get_db] = lambda: session_factory()

    # Build the ASGI transport client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as asgi_client:
        yield asgi_client

    app.dependency_overrides.clear()


# ── Test user (admin) ─────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def admin_user(session_factory: async_sessionmaker[AsyncSession]) -> dict:
    """Creates and persists an admin user; returns dict with raw fields for JWT calls."""
    async with session_factory() as session:
        from app.api.deps import hash_password

        admin = User(
            id=uuid.uuid4(),
            username="testadmin",
            role="admin",
            password_hash=hash_password("testpassword123"),
            created_at=datetime.now(timezone.utc),
        )
        session.add(admin)
        await session.commit()
        # Re-fetch to get DB-populated fields
        await session.refresh(admin)

    return {
        "id": str(admin.id),
        "username": admin.username,
        "password": "testpassword123",
        "role": admin.role,
    }


# ── JWT-bearer auth header ─────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def auth_header(client: AsyncClient, admin_user: dict) -> dict:
    """Returns a dict with a valid Authorization: Bearer header for API calls."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_user["username"], "password": admin_user["password"]},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Celery dispatch stub ───────────────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
def stub_celery_dispatch(monkeypatch: pytest.MonkeyPatch):
    """Replace _dispatch_async with a no-op so ingestion tests don't need Redis."""
    import app.services.celery_client as celery_client

    monkeypatch.setattr(celery_client, "_dispatch_async", lambda job_id, payload: "stubbed")