import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_login_access_token(async_client: AsyncClient, db_session):
    # User creation is handled in conftest or we can create one here if needed
    # But since we need a user to log in, let's create one first
    from app.models.user import User, UserProfile
    from app.core.security import get_password_hash
    
    email = "auth_test@example.com"
    password = "password123"
    hashed = get_password_hash(password)
    
    user = User(email=email, password_hash=hashed, username="auth_test")
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(user_id=user.id, full_name="Auth Test")
    db_session.add(profile)
    await db_session.commit()
    
    login_data = {
        "username": email,
        "password": password
    }
    
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, db_session):
    # Create user
    from app.models.user import User, UserProfile
    from app.core.security import get_password_hash
    
    email = "wrong_pass_test@example.com"
    password = "password123"
    hashed = get_password_hash(password)
    
    user = User(email=email, password_hash=hashed, username="wrong_pass_test")
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(user_id=user.id, full_name="Auth Test")
    db_session.add(profile)
    await db_session.commit()
    
    login_data = {
        "username": email,
        "password": "wrongpassword"
    }
    
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)
    assert response.status_code == 400
