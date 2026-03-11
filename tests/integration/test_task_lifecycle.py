"""
Integration test: Task CRUD lifecycle.

Create course → Create task → Read tasks → Update task → Delete task.
Verifies the full task management flow with authentication.
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from app.core.config import settings

API = settings.API_V1_STR


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_crud_lifecycle(async_client: AsyncClient, normal_user_token_headers: dict):
    """Full task lifecycle: create course → create task → update → delete."""
    headers = normal_user_token_headers

    import uuid
    uid = uuid.uuid4().hex[:6]
    # ── 1. Create a course ───────────────────────────────────────────
    course_data = {"name": f"Integration Test Course {uid}", "color_code": "#ABCDEF"}
    r = await async_client.post(f"{API}/courses/", headers=headers, json=course_data)
    assert r.status_code == 200, f"Create course failed: {r.text}"
    course = r.json()
    course_id = course["id"]
    assert course["name"] == f"Integration Test Course {uid}"

    # ── 2. Create a task under that course ────────────────────────────
    start = (datetime.utcnow() + timedelta(days=5)).isoformat()
    end = (datetime.utcnow() + timedelta(days=5, hours=2)).isoformat()

    task_data = {
        "title": "Integration Task",
        "course_id": course_id,
        "priority": "High",
        "category": "Assignment",
        "scheduled_start_time": start,
        "scheduled_end_time": end,
    }
    r = await async_client.post(f"{API}/tasks/", headers=headers, json=task_data)
    assert r.status_code == 200, f"Create task failed: {r.text}"
    task = r.json()
    task_id = task["id"]
    assert task["title"] == "Integration Task"
    assert task["course_id"] == course_id

    # ── 3. Read tasks — should include our new task ──────────────────
    r = await async_client.get(f"{API}/tasks/", headers=headers)
    assert r.status_code == 200
    tasks = r.json()
    assert any(t["id"] == task_id for t in tasks), "Created task not found in list"

    # ── 4. Update the task title ─────────────────────────────────────
    r = await async_client.patch(
        f"{API}/tasks/{task_id}",
        headers=headers,
        json={"title": "Updated Integration Task"},
    )
    assert r.status_code == 200, f"Update task failed: {r.text}"
    assert r.json()["title"] == "Updated Integration Task"

    # ── 5. Delete the task ───────────────────────────────────────────
    r = await async_client.delete(f"{API}/tasks/{task_id}", headers=headers)
    assert r.status_code == 200, f"Delete task failed: {r.text}"

    # ── 6. Verify the task is gone ───────────────────────────────────
    r = await async_client.get(f"{API}/tasks/", headers=headers)
    assert r.status_code == 200
    assert not any(t["id"] == task_id for t in r.json()), "Deleted task still in list"

    # ── 7. Clean up: delete the course ───────────────────────────────
    r = await async_client.delete(f"{API}/courses/{course_id}", headers=headers)
    assert r.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_belongs_to_correct_course(async_client: AsyncClient, normal_user_token_headers: dict):
    """Verify a task created under Course A shows course A's ID."""
    headers = normal_user_token_headers

    import uuid
    uid = uuid.uuid4().hex[:6]
    # Create two courses
    r1 = await async_client.post(f"{API}/courses/", headers=headers, json={"name": f"Course Alpha {uid}", "color_code": "#111111"})
    r2 = await async_client.post(f"{API}/courses/", headers=headers, json={"name": f"Course Beta {uid}", "color_code": "#222222"})
    assert r1.status_code == 200 and r2.status_code == 200
    cid_a = r1.json()["id"]
    cid_b = r2.json()["id"]

    # Create task under Course Alpha
    start = (datetime.utcnow() + timedelta(days=15)).isoformat()
    end = (datetime.utcnow() + timedelta(days=15, hours=1)).isoformat()
    task_data = {
        "title": "Alpha Task",
        "course_id": cid_a,
        "scheduled_start_time": start,
        "scheduled_end_time": end,
    }
    r = await async_client.post(f"{API}/tasks/", headers=headers, json=task_data)
    assert r.status_code == 200
    assert r.json()["course_id"] == cid_a
    assert r.json()["course_id"] != cid_b
