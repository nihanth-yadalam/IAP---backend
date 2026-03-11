"""
Integration test: Full user lifecycle.

Register → Login → GET /me → Update profile → Login with wrong password.

Uses the async_client + db_session fixtures from tests/conftest.py
(real DB via Neon, session-scoped engine).
"""

import uuid
import pytest
from httpx import AsyncClient
from app.core.config import settings

API = settings.API_V1_STR


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_user_lifecycle(async_client: AsyncClient, db_session):
    """Register, confirm email, login, read profile, update profile — all in sequence."""

    # ── 1. Register ──────────────────────────────────────────────────
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"integ_user_{uid}@example.com",
        "username": f"integ_user_{uid}",
        "password": "IntegTest@123",
    }
    r = await async_client.post(f"{API}/users/", json=register_payload)
    assert r.status_code in (200, 201), f"Register failed: {r.text}"
    reg_data = r.json()
    assert reg_data.get("email") == register_payload["email"] or "message" in reg_data

    # ── 2. Confirm email in DB (simulate email confirmation) ─────────
    from sqlalchemy import update
    from app.models.user import User
    await db_session.execute(
        update(User)
        .where(User.email == register_payload["email"])
        .values(email_confirmed=True)
    )
    await db_session.commit()

    # ── 3. Login ─────────────────────────────────────────────────────
    login_data = {
        "username": register_payload["email"],
        "password": register_payload["password"],
    }
    r = await async_client.post(f"{API}/auth/login/access-token", data=login_data)
    assert r.status_code == 200, f"Login failed: {r.text}"
    login_resp = r.json()

    if "access_token" in login_resp:
        # Direct token (no MFA)
        tokens = login_resp
    elif login_resp.get("status") == "otp_pending":
        # MFA flow: read OTP from DB and verify
        from app.models.user import OTPCode, User as UserModel
        from sqlalchemy import select as sa_select
        user_result = await db_session.execute(
            sa_select(UserModel).where(UserModel.email == register_payload["email"])
        )
        user_obj = user_result.scalars().first()
        otp_result = await db_session.execute(
            sa_select(OTPCode).where(OTPCode.user_id == user_obj.id, OTPCode.purpose == "login")
        )
        otp_record = otp_result.scalars().first()
        assert otp_record, "OTP record not found"

        r2 = await async_client.post(
            f"{API}/auth/login/verify-otp",
            json={"email": register_payload["email"], "otp": otp_record.code}
        )
        tokens = r2.json()
    else:
        raise AssertionError(f"Unexpected login response: {login_resp}")

    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # ── 4. GET /users/me ─────────────────────────────────────────────
    r = await async_client.get(f"{API}/users/me", headers=headers)
    assert r.status_code == 200, f"GET /me failed: {r.text}"
    me = r.json()
    assert me["email"] == register_payload["email"]

    # ── 5. Update profile ────────────────────────────────────────────
    r = await async_client.put(
        f"{API}/users/me/profile",
        headers=headers,
        json={"full_name": "Integration Tester"},
    )
    assert r.status_code == 200, f"Update profile failed: {r.text}"

    # ── 6. Login with WRONG password ─────────────────────────────────
    bad_login = {
        "username": register_payload["email"],
        "password": "WrongPassword!",
    }
    r = await async_client.post(f"{API}/auth/login/access-token", data=bad_login)
    assert r.status_code == 400, "Expected 400 for wrong password"
