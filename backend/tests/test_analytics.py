"""Analytics API tests — GET /analytics/summary."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_summary(client: AsyncClient, auth_header: dict):
    """GET /analytics/summary returns 200 with total_violations and by_type."""
    response = await client.get(
        "/api/v1/analytics/summary",
        headers=auth_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert "total_violations" in body
    assert "by_type" in body
    assert isinstance(body["total_violations"], int)
    assert isinstance(body["by_type"], dict)


@pytest.mark.asyncio
async def test_analytics_summary_with_date_range(
    client: AsyncClient,
    auth_header: dict,
):
    """date_from and date_to query params are accepted without error."""
    response = await client.get(
        "/api/v1/analytics/summary",
        params={"date_from": "2024-01-01", "date_to": "2024-12-31"},
        headers=auth_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert "total_violations" in body


@pytest.mark.asyncio
async def test_analytics_requires_auth(client: AsyncClient):
    """Unauthenticated request returns 401."""
    response = await client.get("/api/v1/analytics/summary")
    assert response.status_code == 401