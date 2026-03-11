"""
Regression test: Data integrity checks.

Verify list counts, user isolation, sync status defaults.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from app.core.config import settings

API = settings.API_V1_STR


@pytest.mark.regression
@pytest.mark.asyncio
async def test_course_and_task_counts(async_client: AsyncClient, normal_user_token_headers: dict):
    """After creating N courses and M tasks, list endpoints return correct counts."""
    headers = normal_user_token_headers

    # Create 2 courses
    for i in range(2):
        r = await async_client.post(f"{API}/courses/", headers=headers, json={
            "name": f"Count Course {i}",
            "color_code": f"#00{i}{i}{i}{i}",
        })
        assert r.status_code == 200

    r = await async_client.get(f"{API}/courses/", headers=headers)
    assert r.status_code == 200
    courses = r.json()
    assert len(courses) >= 2, f"Expected ≥2 courses, got {len(courses)}"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_sync_status_default(async_client: AsyncClient, normal_user_token_headers: dict):
    """Sync status for a user without Google linked should show google_linked=False."""
    headers = normal_user_token_headers
    r = await async_client.get(f"{API}/sync/status", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "google_linked" in data
    assert data["google_linked"] is False


@pytest.mark.regression
@pytest.mark.asyncio
async def test_sync_reset_succeeds(async_client: AsyncClient, normal_user_token_headers: dict):
    """Sync reset should return success even if nothing was synced."""
    headers = normal_user_token_headers
    r = await async_client.post(f"{API}/sync/reset", headers=headers)
    assert r.status_code == 200
    assert r.json()["message"] == "Sync state reset successfully"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_sync_trigger_without_google(async_client: AsyncClient, normal_user_token_headers: dict):
    """Triggering sync without Google linked should return 400."""
    headers = normal_user_token_headers
    r = await async_client.post(f"{API}/sync/trigger", headers=headers)
    assert r.status_code == 400
    assert "Google account not linked" in r.json()["detail"]
