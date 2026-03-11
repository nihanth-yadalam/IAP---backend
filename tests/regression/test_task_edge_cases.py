"""
Regression test: Task edge cases.

Collision detection, invalid data, nonexistent resources.
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from app.core.config import settings

API = settings.API_V1_STR


@pytest.mark.regression
@pytest.mark.asyncio
async def test_task_time_collision(async_client: AsyncClient, normal_user_token_headers: dict):
    """Two tasks with overlapping time slots should return 409."""
    headers = normal_user_token_headers

    import uuid
    uid = uuid.uuid4().hex[:6]
    # Create course
    r = await async_client.post(f"{API}/courses/", headers=headers, json={"name": f"Collision Regress Course {uid}", "color_code": "#AABB00"})
    assert r.status_code == 200
    course_id = r.json()["id"]

    base = datetime.utcnow() + timedelta(days=30)
    start1 = base.isoformat()
    end1 = (base + timedelta(hours=2)).isoformat()

    # Task 1
    r = await async_client.post(f"{API}/tasks/", headers=headers, json={
        "title": "Regression Task 1",
        "course_id": course_id,
        "scheduled_start_time": start1,
        "scheduled_end_time": end1,
        "priority": "Medium",
        "category": "Study",
    })
    assert r.status_code == 200

    # Task 2 — overlaps with Task 1
    overlap_start = (base + timedelta(hours=1)).isoformat()
    overlap_end = (base + timedelta(hours=3)).isoformat()
    r = await async_client.post(f"{API}/tasks/", headers=headers, json={
        "title": "Regression Task 2 Overlap",
        "course_id": course_id,
        "scheduled_start_time": overlap_start,
        "scheduled_end_time": overlap_end,
        "priority": "Low",
        "category": "Assignment",
    })
    assert r.status_code == 409, f"Expected 409 for time collision, got {r.status_code}: {r.text}"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_update_nonexistent_task(async_client: AsyncClient, normal_user_token_headers: dict):
    """Updating a task that doesn't exist should return 404."""
    headers = normal_user_token_headers
    r = await async_client.patch(f"{API}/tasks/999999", headers=headers, json={"title": "Ghost"})
    assert r.status_code == 404


@pytest.mark.regression
@pytest.mark.asyncio
async def test_delete_nonexistent_task(async_client: AsyncClient, normal_user_token_headers: dict):
    """Deleting a task that doesn't exist should return 404."""
    headers = normal_user_token_headers
    r = await async_client.delete(f"{API}/tasks/999999", headers=headers)
    assert r.status_code == 404


@pytest.mark.regression
@pytest.mark.asyncio
async def test_create_task_with_nonexistent_course(async_client: AsyncClient, normal_user_token_headers: dict):
    """Creating a task linked to a nonexistent course should fail."""
    headers = normal_user_token_headers
    start = (datetime.utcnow() + timedelta(days=50)).isoformat()
    end = (datetime.utcnow() + timedelta(days=50, hours=1)).isoformat()

    r = await async_client.post(f"{API}/tasks/", headers=headers, json={
        "title": "Orphan Task",
        "course_id": 999999,
        "scheduled_start_time": start,
        "scheduled_end_time": end,
        "priority": "Low",
    })
    assert r.status_code == 404, f"Expected 404 for nonexistent course, got {r.status_code}"
