"""Async DB helpers used by the CV pipeline worker.

Kept intentionally minimal: the worker needs only to update Violation rows
based on pipeline results, so a thin asyncpg wrapper is enough. We avoid
copying all of the backend's SQLAlchemy models to keep the worker
decoupled from schema migrations.

Each task runs the pool inside a single `asyncio.run()` block. The pool
is bound to that event loop and torn down at the end so subsequent
tasks (which Celery may execute with a fresh loop) can create their own
pool without "Event loop is closed" errors from asyncpg.
"""

import logging
from typing import Any

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)


async def _create_pool() -> asyncpg.Pool:
    """Create a fresh asyncpg pool bound to the *current* event loop."""
    url = settings.resolved_database_url.replace("+asyncpg", "")
    return await asyncpg.create_pool(url, min_size=1, max_size=4)


async def fetch_one(query: str, *args: Any) -> asyncpg.Record | None:
    """Open a pool, run a single read, close the pool (one loop, lifetime bound)."""
    pool = await _create_pool()
    try:
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    finally:
        await pool.close()


async def execute(query: str, *args: Any) -> str:
    """Open a pool, run a single write, close the pool (one loop, lifetime bound)."""
    pool = await _create_pool()
    try:
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)
    finally:
        await pool.close()
