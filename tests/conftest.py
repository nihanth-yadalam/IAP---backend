import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.config import settings
from app.api.deps import get_db
from app.models.user import User, UserProfile
from app.core.security import get_password_hash
from unittest.mock import patch

print(f"DEBUG IN CONFTEST: DATABASE_URL={settings.DATABASE_URL}")

@pytest.fixture(scope="session", autouse=True)
def mock_scheduler():
    with patch("app.main.start_scheduler"), patch("app.main.stop_scheduler"):
        yield


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh engine + session PER TEST to avoid event-loop conflicts.
    Each test function gets its own event loop from pytest-asyncio,
    so the engine must be created inside that loop.
    """
    _engine = create_async_engine(settings.DATABASE_URL, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _session_factory() as session:
        yield session
    await _engine.dispose()


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture for creating an AsyncClient with an overridden get_db dependency.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def normal_user_token_headers(async_client: AsyncClient, db_session: AsyncSession) -> dict:
    """
    Creates a test user and returns authentication headers.
    """
    import uuid
    uid = uuid.uuid4().hex[:8]
    email = f"test_user_{uid}@example.com"
    username = f"test_user_{uid}"
    password = "testpassword"
    
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            username=username,
            email_confirmed=True,
        )
        db_session.add(user)
        await db_session.flush()
        
        profile = UserProfile(
            user_id=user.id,
            full_name="Test User"
        )
        db_session.add(profile)
        await db_session.commit()
    
    login_data = {
        "username": email,
        "password": password
    }
    r = await async_client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)
    login_resp = r.json()

    if "access_token" in login_resp:
        # Direct token (no MFA)
        a_token = login_resp["access_token"]
    elif login_resp.get("status") == "otp_pending":
        # MFA flow: read OTP from DB and verify
        from app.models.user import OTPCode
        otp_result = await db_session.execute(
            select(OTPCode).where(OTPCode.user_id == user.id, OTPCode.purpose == "login")
        )
        otp_record = otp_result.scalars().first()
        assert otp_record, "OTP record not found in DB after login"

        r2 = await async_client.post(
            f"{settings.API_V1_STR}/auth/login/verify-otp",
            json={"email": email, "otp": otp_record.code}
        )
        tokens = r2.json()
        assert "access_token" in tokens, f"OTP verify failed: {tokens}"
        a_token = tokens["access_token"]
    else:
        raise AssertionError(f"Unexpected login response: {login_resp}")

    headers = {"Authorization": f"Bearer {a_token}"}
    return headers
