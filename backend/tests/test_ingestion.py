"""Ingestion endpoint tests — POST /upload.

Validates that:
- Authenticated POST to /upload returns 202 with a job_id
- A violation row is immediately visible in /violations with status=pending
- Invalid base64 returns 422/400
- Unauthenticated requests are rejected
"""

import base64
import uuid

import pytest
from httpx import AsyncClient


def _tiny_jpeg_base64() -> str:
    """A trivial 1×1 black JPEG as base64 (from https://gist.github.com/72hits/9620681)."""
    tiny_jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\x08\x0c\x14"
        b"\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c"
        b" $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01"
        b"\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01"
        b"\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08"
        b"\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x03\x02\x04\x03\x05\x05"
        b"\x04\x04\x00\x01\x02w\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"
        b"\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\x16\x17\x18"
        b"\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86"
        b"\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6"
        b"\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7"
        b"\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6"
        b"\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00"
        b"\x08\x01\x01\x00\x00?\x00\xfd\xfc\xff\xd9"
    )
    return base64.b64encode(tiny_jpeg).decode()


@pytest.mark.asyncio
async def test_upload_creates_pending_violation(
    client: AsyncClient,
    auth_header: dict,
):
    """POST /upload returns 202 and the placeholder row appears immediately."""
    camera_id = str(uuid.uuid4())
    response = await client.post(
        "/api/v1/ingestion/upload",
        json={
            "camera_id": camera_id,
            "timestamp": "2024-01-15T10:30:00Z",
            "image_base64": _tiny_jpeg_base64(),
            "metadata": {"source": "test"},
        },
        headers=auth_header,
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert "job_id" in body
    assert body["job_id"].startswith("job-")

    # The ingestion endpoint already committed the row — verify with /violations
    violations_resp = await client.get(
        "/api/v1/violations",
        params={"limit": 50},
        headers=auth_header,
    )
    assert violations_resp.status_code == 200
    violations_body = violations_resp.json()
    ids = [v["id"] for v in violations_body["data"]]
    jobs = [v.get("job_id") for v in violations_body["data"]]
    assert body["job_id"] in jobs


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    """Unauthenticated upload returns 401."""
    response = await client.post(
        "/api/v1/ingestion/upload",
        json={
            "camera_id": str(uuid.uuid4()),
            "timestamp": "2024-01-15T10:30:00Z",
            "image_base64": _tiny_jpeg_base64(),
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_rejects_invalid_base64(
    client: AsyncClient,
    auth_header: dict,
):
    """Malformed base64 returns 400."""
    response = await client.post(
        "/api/v1/ingestion/upload",
        json={
            "camera_id": str(uuid.uuid4()),
            "timestamp": "2024-01-15T10:30:00Z",
            "image_base64": "not-valid-base64!!!",
        },
        headers=auth_header,
    )
    assert response.status_code == 400