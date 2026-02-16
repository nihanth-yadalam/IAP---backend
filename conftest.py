"""
Root conftest — shared fixtures for the entire IAP-backend test suite.

Strategy:
  • Replace the async PostgreSQL engine with an in-memory SQLite engine
    so tests run without a live database.
  • Override the FastAPI `get_db` dependency to use the test session.
  • Provide helper fixtures: `client`, `auth_headers`, `test_user`, etc.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Patch bcrypt (bcrypt ≥ 4.1.0 removed __about__)
# ---------------------------------------------------------------------------
import bcrypt

if not hasattr(bcrypt, "__about__"):
    class _About:
        __version__ = bcrypt.__version__
    bcrypt.__about__ = _About()

# ---------------------------------------------------------------------------
# Import AFTER bcrypt patch so passlib doesn't choke
# ---------------------------------------------------------------------------
from app.db.base import Base
from app.api.deps import get_db
from app.main import app as fastapi_app
from app.core import security

# ---------------------------------------------------------------------------
# Test-scoped async engine (sqlite+aiosqlite, in-memory)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=engine_test,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Event-loop fixture (session-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# DB tables — create once, wipe rows between tests
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(autouse=True)
async def _prepare_db():
    """Create all tables before each test; drop them after."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Override get_db dependency
# ---------------------------------------------------------------------------
async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session

fastapi_app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Async HTTP client
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helper: Register and return (user_dict, plain_password)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def registered_user(client: AsyncClient):
    """Register a fresh user and return (response_json, plain_password)."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    payload = {
        "email": f"test{uid}@example.com",
        "username": f"user{uid}",
        "password": "Str0ngP@ss!",
    }
    resp = await client.post("/api/v1/users/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json(), payload["password"]


# ---------------------------------------------------------------------------
# Helper: Auth headers for a registered user
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user):
    """Login the registered user and return {'Authorization': 'Bearer …'}."""
    user_data, password = registered_user
    resp = await client.post(
        "/api/v1/login/access-token",
        data={"username": user_data["email"], "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
