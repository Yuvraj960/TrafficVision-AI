"""Auth endpoint tests — login, token refresh, logout.

POST /api/v1/auth/login  (form-data: username, password)
GET  /api/v1/auth/me     (Bearer token)
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user: dict):
    """A valid username/password pair returns an access token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_user["username"], "password": admin_user["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_bad_password(client: AsyncClient, admin_user: dict):
    """Wrong password returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_user["username"], "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    """Unknown username returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "does_not_exist", "password": "anypassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me(client: AsyncClient, auth_header: dict):
    """GET /auth/me returns the authenticated user's profile."""
    response = await client.get("/api/v1/auth/me", headers=auth_header)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "testadmin"
    assert body["role"] == "admin"
    assert "id" in body


@pytest.mark.asyncio
async def test_auth_me_no_token(client: AsyncClient):
    """Request without a token returns 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_invalid_token(client: AsyncClient):
    """Request with an invalid token returns 401."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.valid.token"},
    )
    assert response.status_code == 401