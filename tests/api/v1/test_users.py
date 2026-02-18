import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_create_user(async_client: AsyncClient):
    data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "password123"
    }
    response = await async_client.post(f"{settings.API_V1_STR}/users/", json=data)
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == data["email"]
    assert "id" in content

@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client: AsyncClient, db_session):
    # Preset user
    from app.models.user import User, UserProfile
    from app.core.security import get_password_hash
    
    email = "duplicate@example.com"
    password = "password123"
    user = User(email=email, password_hash=get_password_hash(password), username="dup")
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(user_id=user.id, full_name="Dup")
    db_session.add(profile)
    await db_session.commit()
    
    data = {
        "email": email,
        "username": "newuser_dup",
        "password": "password123"
    }
    response = await async_client.post(f"{settings.API_V1_STR}/users/", json=data)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_read_users_me(async_client: AsyncClient, normal_user_token_headers):
    response = await async_client.get(f"{settings.API_V1_STR}/users/me", headers=normal_user_token_headers)
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == "test_user_pytest@example.com"

@pytest.mark.asyncio
async def test_update_user_profile(async_client: AsyncClient, normal_user_token_headers):
    data = {"full_name": "Updated Name"}
    response = await async_client.put(f"{settings.API_V1_STR}/users/me/profile", headers=normal_user_token_headers, json=data)
    assert response.status_code == 200
    content = response.json()
    assert content["full_name"] == "Updated Name"
