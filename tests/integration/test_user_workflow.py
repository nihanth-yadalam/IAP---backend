"""
Integration test: Full user lifecycle.

Register → Login → GET /me → Update profile → Login with wrong password.

Uses the async_client + db_session fixtures from tests/conftest.py
(real DB via Neon, session-scoped engine).
"""

import pytest
from httpx import AsyncClient
from app.core.config import settings

API = settings.API_V1_STR


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_user_lifecycle(async_client: AsyncClient):
    """Register, login, read profile, update profile — all in sequence."""

    # ── 1. Register ──────────────────────────────────────────────────
    register_payload = {
        "email": "integ_user@example.com",
        "username": "integ_user",
        "password": "IntegTest@123",
    }
    r = await async_client.post(f"{API}/users/", json=register_payload)
    assert r.status_code == 200, f"Register failed: {r.text}"
    user_data = r.json()
    assert user_data["email"] == register_payload["email"]
    assert "id" in user_data

    # ── 2. Login ─────────────────────────────────────────────────────
    login_data = {
        "username": register_payload["email"],
        "password": register_payload["password"],
    }
    r = await async_client.post(f"{API}/auth/login/access-token", data=login_data)
    assert r.status_code == 200, f"Login failed: {r.text}"
    tokens = r.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # ── 3. GET /users/me ─────────────────────────────────────────────
    r = await async_client.get(f"{API}/users/me", headers=headers)
    assert r.status_code == 200, f"GET /me failed: {r.text}"
    me = r.json()
    assert me["email"] == register_payload["email"]

    # ── 4. Update profile ────────────────────────────────────────────
    r = await async_client.put(
        f"{API}/users/me/profile",
        headers=headers,
        json={"full_name": "Integration Tester"},
    )
    assert r.status_code == 200, f"Update profile failed: {r.text}"

    # ── 5. Login with WRONG password ─────────────────────────────────
    bad_login = {
        "username": register_payload["email"],
        "password": "WrongPassword!",
    }
    r = await async_client.post(f"{API}/auth/login/access-token", data=bad_login)
    assert r.status_code == 400, "Expected 400 for wrong password"
