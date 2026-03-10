"""
Integration Tests: User Profile Flow
=======================================
Tests user profile management:
  - Get current user info
  - Update profile fields (name, major, university)
  - Change password (correct & wrong current password)
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_get_current_user(client: AsyncClient, auth_headers: dict):
    """GET /users/me returns the logged-in user's data."""
    resp = await client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "integration@testuser.com"
    assert data["username"] == "integration_user"
    assert "profile" in data


async def test_update_user_profile(client: AsyncClient, auth_headers: dict):
    """PUT /users/me/profile updates profile fields."""
    resp = await client.put(
        "/api/v1/users/me/profile",
        headers=auth_headers,
        json={
            "full_name": "Integration Tester",
            "major": "Software Engineering",
            "university": "Test University",
            "timezone": "Asia/Kolkata",
        },
    )
    assert resp.status_code == 200


async def test_update_profile_partial(client: AsyncClient, auth_headers: dict):
    """Partial profile update only changes provided fields."""
    # First set a full profile
    await client.put(
        "/api/v1/users/me/profile",
        headers=auth_headers,
        json={"full_name": "Original Name", "major": "CS"},
    )

    # Now update only major
    resp = await client.put(
        "/api/v1/users/me/profile",
        headers=auth_headers,
        json={"major": "Data Science"},
    )
    assert resp.status_code == 200


async def test_change_password_correct_current(client: AsyncClient):
    """POST /users/me/password succeeds with correct current password."""
    email = "changepw@test.com"
    old_pw = "OldPass1!"
    new_pw = "NewPass2!"

    # Register
    await client.post("/api/v1/users/", json={
        "email": email, "password": old_pw, "username": "changepw"
    })

    # Login
    login = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": email, "password": old_pw},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Change password
    resp = await client.post(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": old_pw, "new_password": new_pw},
    )
    assert resp.status_code == 200

    # Old password should no longer work
    bad_login = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": email, "password": old_pw},
    )
    assert bad_login.status_code == 400

    # New password should work
    good_login = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": email, "password": new_pw},
    )
    assert good_login.status_code == 200


async def test_change_password_wrong_current(client: AsyncClient, auth_headers: dict):
    """POST /users/me/password with wrong current password returns 400."""
    resp = await client.post(
        "/api/v1/users/me/password",
        headers=auth_headers,
        json={"current_password": "NotTheRealPassword!", "new_password": "NewOne1!"},
    )
    assert resp.status_code == 400


async def test_change_password_same_as_current(client: AsyncClient, auth_headers: dict):
    """Setting new password equal to current should return 400."""
    same_pw = "IntegrationPass1!"
    resp = await client.post(
        "/api/v1/users/me/password",
        headers=auth_headers,
        json={"current_password": same_pw, "new_password": same_pw},
    )
    assert resp.status_code == 400
