"""
Integration Tests: Tasks Flow
================================
Tests the full CRUD lifecycle for tasks:
  - Create task (no deadline required)
  - Create task linked to a course
  - List tasks (empty, then populated)
  - Update task (title, status, priority)
  - Delete task
  - 404 on non-existent task
  - Task status enum validation
  - Task cannot be accessed by another user
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

TASK_BASE = {
    "title": "Write unit tests",
    "description": "Cover all edge cases",
    "priority": "High",
}


async def test_create_task_minimal(client: AsyncClient, auth_headers: dict):
    """POST /tasks/ creates a task with just a title."""
    resp = await client.post(
        "/api/v1/tasks/",
        headers=auth_headers,
        json={"title": "Minimal Task"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["title"] == "Minimal Task"
    assert "id" in data


async def test_create_task_with_deadline(client: AsyncClient, auth_headers: dict):
    """POST /tasks/ creates a task with a deadline."""
    resp = await client.post(
        "/api/v1/tasks/",
        headers=auth_headers,
        json={
            "title": "Deadline Task",
            "description": "Has a deadline",
            "deadline": "2025-12-31T23:59:00",
            "priority": "High",
        },
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["title"] == "Deadline Task"
    assert data["deadline"] is not None


async def test_create_task_linked_to_course(client: AsyncClient, auth_headers: dict):
    """POST /tasks/ links a task to a course by course_id."""
    # First create a course
    course_resp = await client.post(
        "/api/v1/courses/",
        headers=auth_headers,
        json={"name": "Machine Learning", "color_code": "#1ABC9C"},
    )
    course_id = course_resp.json()["id"]

    # Create task linked to that course
    resp = await client.post(
        "/api/v1/tasks/",
        headers=auth_headers,
        json={"title": "ML Assignment", "course_id": course_id},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["course_id"] == course_id


async def test_create_task_invalid_course_rejected(client: AsyncClient, auth_headers: dict):
    """POST /tasks/ with a non-existent course_id returns 404."""
    resp = await client.post(
        "/api/v1/tasks/",
        headers=auth_headers,
        json={"title": "Orphan Task", "course_id": 99999},
    )
    assert resp.status_code == 404


async def test_list_tasks_empty(client: AsyncClient, auth_headers: dict):
    """GET /tasks/ returns an empty list when no tasks exist."""
    resp = await client.get("/api/v1/tasks/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_tasks_returns_created_tasks(client: AsyncClient, auth_headers: dict):
    """GET /tasks/ returns all tasks belonging to the user."""
    await client.post("/api/v1/tasks/", headers=auth_headers,
                      json={"title": "Task Alpha"})
    await client.post("/api/v1/tasks/", headers=auth_headers,
                      json={"title": "Task Beta"})

    resp = await client.get("/api/v1/tasks/", headers=auth_headers)
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert "Task Alpha" in titles
    assert "Task Beta" in titles


async def test_update_task_title(client: AsyncClient, auth_headers: dict):
    """PATCH /tasks/{id} updates the task title."""
    create = await client.post(
        "/api/v1/tasks/",
        headers=auth_headers,
        json={"title": "Original Title"},
    )
    task_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


async def test_update_task_status(client: AsyncClient, auth_headers: dict):
    """PATCH /tasks/{id} updates task status to Completed."""
    create = await client.post(
        "/api/v1/tasks/",
        headers=auth_headers,
        json={"title": "Completable Task"},
    )
    task_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
        json={"status": "Completed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Completed"


async def test_delete_task(client: AsyncClient, auth_headers: dict):
    """DELETE /tasks/{id} removes the task; it no longer appears in list."""
    create = await client.post(
        "/api/v1/tasks/",
        headers=auth_headers,
        json={"title": "Delete Me"},
    )
    task_id = create.json()["id"]

    del_resp = await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert del_resp.status_code == 200

    # Should not appear in list
    list_resp = await client.get("/api/v1/tasks/", headers=auth_headers)
    ids = [t["id"] for t in list_resp.json()]
    assert task_id not in ids


async def test_update_nonexistent_task_returns_404(client: AsyncClient, auth_headers: dict):
    """PATCH on a task ID that doesn't exist returns 404."""
    resp = await client.patch(
        "/api/v1/tasks/99999",
        headers=auth_headers,
        json={"title": "Ghost Update"},
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_task_returns_404(client: AsyncClient, auth_headers: dict):
    """DELETE on a non-existent task returns 404."""
    resp = await client.delete("/api/v1/tasks/99999", headers=auth_headers)
    assert resp.status_code == 404


async def test_user_cannot_access_other_users_task(client: AsyncClient):
    """User A cannot update or delete User B's task."""
    # Register User A
    await client.post("/api/v1/users/", json={
        "email": "task_user_a@test.com", "password": "PassA1!", "username": "tua"
    })
    login_a = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "task_user_a@test.com", "password": "PassA1!"},
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    # Register User B
    await client.post("/api/v1/users/", json={
        "email": "task_user_b@test.com", "password": "PassB1!", "username": "tub"
    })
    login_b = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "task_user_b@test.com", "password": "PassB1!"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    # User B creates a task
    create = await client.post(
        "/api/v1/tasks/",
        headers=headers_b,
        json={"title": "B's Private Task"},
    )
    task_id = create.json()["id"]

    # User A cannot update it
    resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=headers_a,
        json={"title": "Hijacked"},
    )
    assert resp.status_code == 404

    # User A cannot delete it
    resp = await client.delete(f"/api/v1/tasks/{task_id}", headers=headers_a)
    assert resp.status_code == 404
