"""
Integration Tests: Courses Flow
=================================
Tests the full CRUD lifecycle for courses:
  - Create a course
  - List courses (only own courses visible)
  - Update a course
  - Delete a course
  - 404 on non-existent course
  - Cannot access other user's courses
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_course(client: AsyncClient, auth_headers: dict):
    """POST /courses/ creates a new course and returns it."""
    resp = await client.post(
        "/api/v1/courses/",
        headers=auth_headers,
        json={"name": "Algorithms", "color_code": "#FF5733"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["name"] == "Algorithms"
    assert "id" in data


async def test_list_courses_empty(client: AsyncClient, auth_headers: dict):
    """GET /courses/ returns an empty list when no courses created."""
    resp = await client.get("/api/v1/courses/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_courses_after_create(client: AsyncClient, auth_headers: dict):
    """GET /courses/ returns created courses."""
    await client.post(
        "/api/v1/courses/",
        headers=auth_headers,
        json={"name": "Database Systems", "color_code": "#3498DB"},
    )
    await client.post(
        "/api/v1/courses/",
        headers=auth_headers,
        json={"name": "Operating Systems", "color_code": "#2ECC71"},
    )

    resp = await client.get("/api/v1/courses/", headers=auth_headers)
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Database Systems" in names
    assert "Operating Systems" in names


async def test_update_course(client: AsyncClient, auth_headers: dict):
    """PATCH /courses/{id} updates a course's name."""
    create = await client.post(
        "/api/v1/courses/",
        headers=auth_headers,
        json={"name": "Old Name", "color_code": "#E74C3C"},
    )
    course_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/courses/{course_id}",
        headers=auth_headers,
        json={"name": "New Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


async def test_delete_course(client: AsyncClient, auth_headers: dict):
    """DELETE /courses/{id} removes a course; it no longer appears in list."""
    create = await client.post(
        "/api/v1/courses/",
        headers=auth_headers,
        json={"name": "To Be Deleted", "color_code": "#95A5A6"},
    )
    course_id = create.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/courses/{course_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200

    # Should not appear in list anymore
    list_resp = await client.get("/api/v1/courses/", headers=auth_headers)
    ids = [c["id"] for c in list_resp.json()]
    assert course_id not in ids


async def test_update_nonexistent_course_returns_404(client: AsyncClient, auth_headers: dict):
    """PATCH on a course ID that doesn't exist returns 404."""
    resp = await client.patch(
        "/api/v1/courses/99999",
        headers=auth_headers,
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_course_returns_404(client: AsyncClient, auth_headers: dict):
    """DELETE on a course ID that doesn't exist returns 404."""
    resp = await client.delete("/api/v1/courses/99999", headers=auth_headers)
    assert resp.status_code == 404


async def test_user_cannot_access_other_users_course(client: AsyncClient):
    """User A cannot update or delete User B's course."""
    # Create User A
    await client.post("/api/v1/users/", json={
        "email": "user_a@courses.com", "password": "PassA1!", "username": "user_a_c"
    })
    login_a = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "user_a@courses.com", "password": "PassA1!"},
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    # Create User B
    await client.post("/api/v1/users/", json={
        "email": "user_b@courses.com", "password": "PassB1!", "username": "user_b_c"
    })
    login_b = await client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "user_b@courses.com", "password": "PassB1!"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    # User B creates a course
    create = await client.post(
        "/api/v1/courses/",
        headers=headers_b,
        json={"name": "B's Private Course", "color_code": "#8E44AD"},
    )
    course_id = create.json()["id"]

    # User A tries to update it — should 404 (ownership check)
    resp = await client.patch(
        f"/api/v1/courses/{course_id}",
        headers=headers_a,
        json={"name": "Hijacked"},
    )
    assert resp.status_code == 404

    # User A tries to delete it — should 404
    resp = await client.delete(f"/api/v1/courses/{course_id}", headers=headers_a)
    assert resp.status_code == 404
