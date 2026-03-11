"""
Regression test: Authentication edge cases.

Duplicate email, missing fields, bad tokens, no-auth access.
"""

import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.security import create_access_token
from datetime import timedelta

API = settings.API_V1_STR


@pytest.mark.regression
@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient, db_session):
    """Registering with an already-taken email should return 400."""
    from app.models.user import User, UserProfile
    from app.core.security import get_password_hash
    import uuid
    uid = uuid.uuid4().hex[:6]

    # Pre-create a user in the DB
    email = f"dup_{uid}@example.com"
    user = User(email=email, password_hash=get_password_hash("pass123"), username=f"dup_{uid}", email_confirmed=True)
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(user_id=user.id, full_name="Dup")
    db_session.add(profile)
    await db_session.commit()

    # Try to register with same email
    r = await async_client.post(f"{API}/users/", json={
        "email": email,
        "username": "different_username",
        "password": "AnotherPass123",
    })
    assert r.status_code == 400
    assert "already exists" in r.json()["detail"].lower()


@pytest.mark.regression
@pytest.mark.asyncio
async def test_register_duplicate_username(async_client: AsyncClient, db_session):
    """Registering with an already-taken username should return 400."""
    from app.models.user import User, UserProfile
    from app.core.security import get_password_hash
    import uuid
    uid = uuid.uuid4().hex[:6]

    username = f"taken_{uid}"
    user = User(email=f"uniq_{uid}@example.com", password_hash=get_password_hash("pass"), username=username, email_confirmed=True)
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(user_id=user.id, full_name="U")
    db_session.add(profile)
    await db_session.commit()

    r = await async_client.post(f"{API}/users/", json={
        "email": f"another_{uid}@example.com",
        "username": username,
        "password": "Pass123!",
    })
    assert r.status_code == 400


@pytest.mark.regression
@pytest.mark.asyncio
async def test_protected_endpoint_without_token(async_client: AsyncClient):
    """Accessing /users/me without auth should return 401."""
    r = await async_client.get(f"{API}/users/me")
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_protected_endpoint_with_bad_token(async_client: AsyncClient):
    """Accessing /users/me with an invalid JWT should return 401/403."""
    headers = {"Authorization": "Bearer this.is.not.a.valid.jwt"}
    r = await async_client.get(f"{API}/users/me", headers=headers)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_expired_token_rejected(async_client: AsyncClient, db_session):
    """An expired JWT should be rejected."""
    from app.models.user import User, UserProfile
    from app.core.security import get_password_hash
    import uuid
    uid = uuid.uuid4().hex[:6]

    user = User(email=f"exp_{uid}@example.com", password_hash=get_password_hash("p"), username=f"exp_{uid}", email_confirmed=True)
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(user_id=user.id, full_name="E")
    db_session.add(profile)
    await db_session.commit()

    # Create a token that already expired
    expired_token = create_access_token(user.id, expires_delta=timedelta(seconds=-10))
    headers = {"Authorization": f"Bearer {expired_token}"}
    r = await async_client.get(f"{API}/users/me", headers=headers)
    assert r.status_code in (401, 403), f"Expected 401/403 for expired token, got {r.status_code}"
