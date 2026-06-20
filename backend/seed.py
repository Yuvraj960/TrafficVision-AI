"""Seed script for TrafficVision AI database.

Inserts a baseline set of cameras, users, and violations so the dashboard has
real data to display on first run. Idempotent — re-running upserts users and
appends new sample violations without duplicating others.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import bcrypt as _bcrypt  # native bcrypt library

# Ensure the backend folder is on sys.path so `app.*` imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import async_session, engine  # noqa: E402
from app.models import AuditLog, Base, Camera, User, Violation  # noqa: E402


def hash_password(plaintext: str) -> str:
    """Hash a password using bcrypt directly (passlib 1.7.4 is incompatible with bcrypt 5.x)."""
    pw_bytes = plaintext.encode("utf-8")[:72]  # bcrypt 72-byte limit
    return _bcrypt.hashpw(pw_bytes, _bcrypt.gensalt(rounds=12)).decode("utf-8")


# ── Image URLs for seed violations (placeholder evidence) ────────────────
SEED_IMAGE_BASE = "https://placehold.co/1280x720/1e293b/818cf8?text=Evidence"
SEED_PLATE_IMAGE = "https://placehold.co/400x100/0f172a/c7d2fe?text=PLATE"


SEED_CAMERAS: list[dict] = [
    {
        "name": "MG Road – Indiranagar Junction",
        "location_lat": 12.9716,
        "location_lng": 77.6411,
        "rtsp_url": "rtsp://camera-001.local/stream",
        "status": "active",
    },
    {
        "name": "Outer Ring Road – Marathahalli Bridge",
        "location_lat": 12.9591,
        "location_lng": 77.6974,
        "rtsp_url": "rtsp://camera-002.local/stream",
        "status": "active",
    },
    {
        "name": "Silk Board Junction",
        "location_lat": 12.9278,
        "location_lng": 77.6236,
        "rtsp_url": "rtsp://camera-003.local/stream",
        "status": "active",
    },
]


SEED_USERS: list[dict] = [
    {
        "username": "admin",
        "role": "admin",
        "password": "admin123",  # Plaintext only here; we hash before insert
    },
    {
        "username": "officer1",
        "role": "officer",
        "password": "officer123",
    },
    {
        "username": "officer2",
        "role": "officer",
        "password": "officer123",
    },
]


def _build_violations(camera_ids: list, reviewer_id: str | None) -> list[dict]:
    """Build a diverse sample of violations across cameras and types."""
    now = datetime.now(timezone.utc)
    samples = [
        {
            "camera_id": camera_ids[0],
            "job_id": "job-seed-0001",
            "violation_type": "helmet",
            "vehicle_type": "motorcycle",
            "plate_number": "MH 12 AB 1234",
            "confidence_score": 0.9210,
            "status": "pending",
            "timestamp": now.replace(hour=8, minute=14, second=0),
            "image_url": f"{SEED_IMAGE_BASE}?text=Helmet+001",
        },
        {
            "camera_id": camera_ids[0],
            "job_id": "job-seed-0002",
            "violation_type": "triple_riding",
            "vehicle_type": "motorcycle",
            "plate_number": "KA 03 MN 4456",
            "confidence_score": 0.8830,
            "status": "pending",
            "timestamp": now.replace(hour=8, minute=42, second=0),
            "image_url": f"{SEED_IMAGE_BASE}?text=Triple",
        },
        {
            "camera_id": camera_ids[1],
            "job_id": "job-seed-0003",
            "violation_type": "wrong_side",
            "vehicle_type": "car",
            "plate_number": "KA 51 HY 7890",
            "confidence_score": 0.7950,
            "status": "approved",
            "reviewed_by": reviewer_id,
            "reviewed_at": now.replace(hour=10, minute=15, second=0),
            "timestamp": now.replace(hour=9, minute=3, second=0),
            "image_url": f"{SEED_IMAGE_BASE}?text=WrongSide",
        },
        {
            "camera_id": camera_ids[1],
            "job_id": "job-seed-0004",
            "violation_type": "stop_line",
            "vehicle_type": "car",
            "plate_number": "TN 22 BC 4321",
            "confidence_score": 0.8640,
            "status": "rejected",
            "reviewed_by": reviewer_id,
            "reviewed_at": now.replace(hour=11, minute=30, second=0),
            "timestamp": now.replace(hour=10, minute=21, second=0),
            "notes": "Signal was green in original feed",
            "image_url": f"{SEED_IMAGE_BASE}?text=StopLine",
        },
        {
            "camera_id": camera_ids[2],
            "job_id": "job-seed-0005",
            "violation_type": "helmet",
            "vehicle_type": "motorcycle",
            "plate_number": "MH 14 DR 9876",
            "confidence_score": 0.9120,
            "status": "pending",
            "timestamp": now.replace(hour=14, minute=5, second=0),
            "image_url": f"{SEED_IMAGE_BASE}?text=Helmet+002",
        },
    ]
    return samples


async def seed() -> None:
    print("[SEED] Starting database seed...")
    async with engine.begin() as conn:
        # Make sure tables exist (no-op if alembic already ran)
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy import select

    async with async_session() as session:
        # ── Users (upsert by username) ──────────────────────────────
        user_ids: dict[str, str] = {}
        for u in SEED_USERS:
            stmt = await session.execute(select(User).where(User.username == u["username"]))
            existing = stmt.scalar_one_or_none()

            if existing is not None:
                user_ids[u["username"]] = str(existing.id)
                print(f"  [.] User '{u['username']}' already exists -> {existing.id}")
            else:
                user = User(
                    username=u["username"],
                    role=u["role"],
                    password_hash=hash_password(u["password"]),
                )
                session.add(user)
                await session.flush()
                user_ids[u["username"]] = str(user.id)
                print(f"  [+] Created user '{u['username']}' -> {user.id}")

        # ── Cameras (insert if missing by name) ──────────────────────
        camera_ids: list[str] = []
        for c in SEED_CAMERAS:
            stmt = await session.execute(select(Camera).where(Camera.name == c["name"]))
            existing = stmt.scalar_one_or_none()
            if existing is not None:
                camera_ids.append(str(existing.id))
                print(f"  [.] Camera '{c['name']}' already exists -> {existing.id}")
            else:
                cam = Camera(**c)
                session.add(cam)
                await session.flush()
                camera_ids.append(str(cam.id))
                print(f"  [+] Created camera '{c['name']}' -> {cam.id}")

        # ── Violations (only insert if table is empty) ───────────────
        existing_rows = (await session.execute(select(Violation))).scalars().all()
        existing_count = len(existing_rows)
        if existing_count > 0:
            print(f"  [.] Skipping violations — {existing_count} already present")
        else:
            reviewer_id = user_ids.get("officer1")
            for v in _build_violations(camera_ids, reviewer_id):
                violation = Violation(
                    **{k: v[k] for k in v if k not in ("reviewed_by", "reviewed_at", "notes")},
                    reviewed_by=v.get("reviewed_by"),
                    reviewed_at=v.get("reviewed_at"),
                    plate_image_url=SEED_PLATE_IMAGE,
                )
                session.add(violation)
            await session.flush()
            print(f"  [+] Inserted {len(SEED_CAMERAS) + 2} sample violations")

            # ── Audit logs for the reviewed ones ───────────────────
            stmt = await session.execute(
                select(Violation).where(Violation.status.in_(["approved", "rejected"]))
            )
            for v in stmt.scalars().all():
                audit = AuditLog(
                    user_id=str(v.reviewed_by) if v.reviewed_by else None,
                    violation_id=v.id,
                    action=v.status,
                    notes=f"Seeded {v.status} action",
                )
                session.add(audit)
            print("  [+] Inserted audit logs for reviewed violations")

        await session.commit()
        print("[DONE] Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
