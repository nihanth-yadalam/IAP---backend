"""
Integration Test Configuration
=================================
Uses an in-memory SQLite database via aiosqlite so integration tests
run completely without an external PostgreSQL server.

Each test function gets a clean database with all tables created fresh,
and a TestClient that overrides the real DB dependency with the test DB.
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.main import app
from app.db.base import Base
from app.api.deps import get_db

# ── SQLite in-memory test database ───────────────────────────────────────────
# "check_same_thread=False" is required for SQLite with async drivers.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:?check_same_thread=False"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh in-memory SQLite database for every test function.
    All tables are created before the test and dropped after.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

    # Import all models so SQLAlchemy knows about them
    import app.models.user      # noqa: F401
    import app.models.task      # noqa: F401
    import app.models.schedule  # noqa: F401
    import app.models.sync      # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
    )

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client that overrides the real DB with the SQLite test DB.
    Uses ASGITransport — no real HTTP server needed.
    """
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client: AsyncClient) -> dict:
    """
    Register a test user, log in, and return Authorization headers.
    Re-usable by any test that needs an authenticated client.
    """
    payload = {
        "email": "integration@testuser.com",
        "password": "IntegrationPass1!",
        "username": "integration_user",
    }

    # Register (ignore 400 = user already exists within same session)
    reg = await client.post("/api/v1/users/", json=payload)
    assert reg.status_code in (200, 201, 400), f"Register failed: {reg.text}"

    # Login
    login = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
