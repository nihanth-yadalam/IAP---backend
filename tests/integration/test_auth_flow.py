"""
Integration Tests: Authentication Flow
========================================
Tests the full auth lifecycle:
  - User registration
  - Duplicate registration rejection
  - Login with correct credentials
  - Login with wrong password
  - Access protected endpoint with valid token
  - Access protected endpoint with no token (401)
  - Access protected endpoint with bad token (401)
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_new_user(client: AsyncClient):
    """A new user can register successfully."""
    resp = await client.post("/api/v1/users/", json={
        "email": "newuser@test.com",
        "password": "SecurePass1!",
        "username": "newuser",
    })
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["email"] == "newuser@test.com"
    assert data["username"] == "newuser"
    assert "id" in data
    # Password must never be returned
    assert "password" not in data
    assert "password_hash" not in data


async def test_register_duplicate_email_rejected(client: AsyncClient):
    """Registering with an email that already exists returns 400."""
    payload = {"email": "dup@test.com", "password": "Pass1!", "username": "dup1"}
    await client.post("/api/v1/users/", json=payload)

    # Second attempt with same email, different username
    resp = await client.post("/api/v1/users/", json={
        "email": "dup@test.com",
        "password": "Pass1!",
        "username": "dup2",
    })
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()


async def test_register_duplicate_username_rejected(client: AsyncClient):
    """Registering with a username that already exists returns 400."""
    await client.post("/api/v1/users/", json={
        "email": "user_a@test.com", "password": "Pass1!", "username": "shared_name"
    })
    resp = await client.post("/api/v1/users/", json={
        "email": "user_b@test.com", "password": "Pass1!", "username": "shared_name"
    })
    assert resp.status_code == 400


async def test_login_with_correct_credentials(client: AsyncClient):
    """Registered user can log in and receives an access token."""
    email, password = "loginok@test.com", "LoginPass1!"
    await client.post("/api/v1/users/", json={
        "email": email, "password": password, "username": "loginok"
    })

    resp = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_with_wrong_password(client: AsyncClient):
    """Login with wrong password returns 400."""
    email = "wrongpass@test.com"
    await client.post("/api/v1/users/", json={
        "email": email, "password": "RealPass1!", "username": "wrongpass"
    })
    resp = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": email, "password": "WrongPass999!"},
    )
    assert resp.status_code == 400


async def test_login_nonexistent_user(client: AsyncClient):
    """Login for a user that was never registered returns 400."""
    resp = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "ghost@test.com", "password": "Ghost1!"},
    )
    assert resp.status_code == 400


async def test_protected_endpoint_with_valid_token(client: AsyncClient, auth_headers: dict):
    """A valid token grants access to /users/me."""
    resp = await client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "integration@testuser.com"


async def test_protected_endpoint_without_token(client: AsyncClient):
    """Accessing a protected endpoint without a token returns 401."""
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_protected_endpoint_with_bad_token(client: AsyncClient):
    """Accessing a protected endpoint with a malformed token returns 401."""
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.token"},
    )
    assert resp.status_code == 401
