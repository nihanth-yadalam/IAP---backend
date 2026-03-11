"""
E2E test: Auth flow against live deployed backend.

Registers a test user, logs in, and calls /users/me.
Requires BACKEND_LIVE_URL environment variable.

⚠️  Creates real data in the production DB. Uses 'e2e_ci_test_*' prefix.
"""

import os
import uuid
import pytest
import httpx

BACKEND_URL = os.getenv("BACKEND_LIVE_URL", "").rstrip("/")
API = f"{BACKEND_URL}/api/v1"

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BACKEND_URL, reason="BACKEND_LIVE_URL not set"),
]


@pytest.mark.asyncio
async def test_live_register_login_me():
    """Register → Login → GET /me on live infra."""
    uid = uuid.uuid4().hex[:8]
    email = f"e2e_ci_test_{uid}@example.com"
    username = f"e2e_{uid}"
    password = "E2eTestP@ss1"

    async with httpx.AsyncClient(timeout=20) as client:
        # ── Register ─────────────────────────────────────────────
        r = await client.post(f"{API}/users/", json={
            "email": email,
            "username": username,
            "password": password,
        })
        # 200 = success, 400 = user already exists (idempotent re-run)
        assert r.status_code in (200, 400), f"Register: {r.status_code} {r.text}"

        # ── Login ────────────────────────────────────────────────
        r = await client.post(f"{API}/auth/login/access-token", data={
            "username": email,
            "password": password,
        })
        assert r.status_code == 200, f"Login: {r.status_code} {r.text}"
        token = r.json()["access_token"]

        # ── GET /users/me ────────────────────────────────────────
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get(f"{API}/users/me", headers=headers)
        assert r.status_code == 200, f"GET /me: {r.status_code} {r.text}"
        assert r.json()["email"] == email
