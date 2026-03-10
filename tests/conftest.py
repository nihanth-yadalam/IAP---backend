import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.api.deps import get_db
from app.models.user import User
from app.core.security import get_password_hash
from unittest.mock import patch

print(f"DEBUG IN CONFTEST: DATABASE_URL={settings.DATABASE_URL}")

@pytest.fixture(scope="session", autouse=True)
def mock_scheduler():
    with patch("app.main.start_scheduler"), patch("app.main.stop_scheduler"):
        yield

print(f"DEBUG IN CONFTEST: DATABASE_URL={settings.DATABASE_URL}")

# Use a separate test database URL if possible, or use the existing one with transaction rollbacks
# For simplicity in this environment, we'll use the existing DB but rely on dependencies.
# ideally: settings.DATABASE_URL + "_test"



@pytest.fixture(scope="session")
async def db_engine():
    """Yields a SQLAlchemy engine which is disposed of after the test session."""
    yield engine
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async database session. 
    In a real-world scenario with a dedicated test DB, we might truncate tables here.
    """
    async with SessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture for creating an AsyncClient with a overridden get_db dependency.
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
    email = "test_user_pytest@example.com"
    password = "testpassword"
    
    # Check if user exists, if so delete to ensure clear state (or just reuse)
    # Ideally tests run in a clean DB. 
    # For now, let's try to register.
    
    # We can also directly insert into DB to avoid side effects of register route
    from app.models.user import User, UserProfile
    
    # We can also directly insert into DB to avoid side effects of register route
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            username="test_user_pytest",
        )
        db_session.add(user)
        await db_session.flush() # flush to get user.id
        
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
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers
