"""
E2E test: Health check against live deployed backend.

Requires BACKEND_LIVE_URL environment variable.
Run manually or via workflow_dispatch CI workflow.
"""

import os
import pytest
import httpx

BACKEND_URL = os.getenv("BACKEND_LIVE_URL", "").rstrip("/")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BACKEND_URL, reason="BACKEND_LIVE_URL not set"),
]


@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /health should return 200 with status=healthy."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{BACKEND_URL}/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_openapi_accessible():
    """GET /api/v1/openapi.json should return 200."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{BACKEND_URL}/api/v1/openapi.json")
    assert r.status_code == 200, f"OpenAPI not accessible: {r.status_code}"
    data = r.json()
    assert "paths" in data, "OpenAPI response missing 'paths' key"
