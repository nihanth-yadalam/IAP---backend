import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_login_access_token(async_client: AsyncClient, db_session):
    # User creation is handled in conftest or we can create one here if needed
    # But since we need a user to log in, let's create one first
    from app.models.user import User, UserProfile
    from app.core.security import get_password_hash
    import uuid
    
    uid = uuid.uuid4().hex[:8]
    email = f"auth_test_{uid}@example.com"
    password = "password123"
    hashed = get_password_hash(password)
    
    user = User(email=email, password_hash=hashed, username=f"auth_test_{uid}", email_confirmed=True)
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
    resp_data = response.json()
    assert resp_data.get("status") == "otp_pending"

@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, db_session):
    # Create user
    from app.models.user import User, UserProfile
    from app.core.security import get_password_hash
    import uuid
    
    uid = uuid.uuid4().hex[:8]
    email = f"wrong_pass_test_{uid}@example.com"
    password = "password123"
    hashed = get_password_hash(password)
    
    user = User(email=email, password_hash=hashed, username=f"wrong_pass_test_{uid}", email_confirmed=True)
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
