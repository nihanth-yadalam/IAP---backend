"""
Integration Tests: Schedule Flow
===================================
Tests the schedule/slots lifecycle:
  - Create a calendar slot
  - List slots (empty, then populated)
  - Update a slot's title and times
  - Soft-delete a slot (it disappears from list)
  - Bulk-create recurring fixed slots
  - 404 on non-existent slot
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_calendar_slot(client: AsyncClient, auth_headers: dict):
    """POST /schedule/slots creates a new calendar slot."""
    resp = await client.post(
        "/api/v1/schedule/slots",
        headers=auth_headers,
        json={
            "title": "Study Session",
            "google_start_datetime": "2025-06-01T10:00:00",
            "google_end_datetime": "2025-06-01T11:00:00",
        },
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["title"] == "Study Session"
    assert "id" in data


async def test_list_slots_empty(client: AsyncClient, auth_headers: dict):
    """GET /schedule/fixed returns empty list when no slots exist."""
    resp = await client.get("/api/v1/schedule/fixed", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_slots_after_create(client: AsyncClient, auth_headers: dict):
    """GET /schedule/fixed returns created slots."""
    await client.post(
        "/api/v1/schedule/slots",
        headers=auth_headers,
        json={
            "title": "Morning Block",
            "google_start_datetime": "2025-06-01T08:00:00",
            "google_end_datetime": "2025-06-01T09:00:00",
        },
    )
    await client.post(
        "/api/v1/schedule/slots",
        headers=auth_headers,
        json={
            "title": "Evening Block",
            "google_start_datetime": "2025-06-01T18:00:00",
            "google_end_datetime": "2025-06-01T19:00:00",
        },
    )

    resp = await client.get("/api/v1/schedule/fixed", headers=auth_headers)
    assert resp.status_code == 200
    titles = [s["title"] for s in resp.json()]
    assert "Morning Block" in titles
    assert "Evening Block" in titles


async def test_update_slot(client: AsyncClient, auth_headers: dict):
    """PUT /schedule/slots/{id} updates a slot's title."""
    create = await client.post(
        "/api/v1/schedule/slots",
        headers=auth_headers,
        json={
            "title": "Old Slot",
            "google_start_datetime": "2025-07-01T09:00:00",
            "google_end_datetime": "2025-07-01T10:00:00",
        },
    )
    slot_id = create.json()["id"]

    resp = await client.put(
        f"/api/v1/schedule/slots/{slot_id}",
        headers=auth_headers,
        json={"title": "Renamed Slot"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Renamed Slot"


async def test_delete_slot_removes_from_list(client: AsyncClient, auth_headers: dict):
    """DELETE /schedule/slots/{id} soft-deletes slot; it disappears from list."""
    create = await client.post(
        "/api/v1/schedule/slots",
        headers=auth_headers,
        json={
            "title": "Temporary Slot",
            "google_start_datetime": "2025-08-01T14:00:00",
            "google_end_datetime": "2025-08-01T15:00:00",
        },
    )
    slot_id = create.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/schedule/slots/{slot_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Should not appear in the list anymore (soft-deleted)
    list_resp = await client.get("/api/v1/schedule/fixed", headers=auth_headers)
    ids = [s["id"] for s in list_resp.json()]
    assert slot_id not in ids


async def test_bulk_create_recurring_slots(client: AsyncClient, auth_headers: dict):
    """POST /schedule/fixed bulk-creates recurring weekly slots."""
    resp = await client.post(
        "/api/v1/schedule/fixed",
        headers=auth_headers,
        json=[
            {"day_of_week": "Monday",    "start_time": "09:00:00", "end_time": "10:00:00", "label": "Lecture"},
            {"day_of_week": "Wednesday", "start_time": "14:00:00", "end_time": "15:30:00", "label": "Lab"},
            {"day_of_week": "Friday",    "start_time": "11:00:00", "end_time": "12:00:00", "label": "Tutorial"},
        ],
    )
    assert resp.status_code == 200
    assert "3" in resp.json()["message"]

    # Recurring slots should appear in the fixed list
    list_resp = await client.get("/api/v1/schedule/fixed", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 3


async def test_bulk_create_replaces_existing_recurring(client: AsyncClient, auth_headers: dict):
    """Calling POST /schedule/fixed again replaces all previous recurring slots."""
    # First bulk create
    await client.post(
        "/api/v1/schedule/fixed",
        headers=auth_headers,
        json=[
            {"day_of_week": "Monday", "start_time": "09:00:00", "end_time": "10:00:00", "label": "Old"},
            {"day_of_week": "Tuesday", "start_time": "10:00:00", "end_time": "11:00:00", "label": "Old2"},
        ],
    )

    # Second bulk create — should replace the first
    resp = await client.post(
        "/api/v1/schedule/fixed",
        headers=auth_headers,
        json=[
            {"day_of_week": "Friday", "start_time": "15:00:00", "end_time": "16:00:00", "label": "New"},
        ],
    )
    assert resp.status_code == 200

    list_resp = await client.get("/api/v1/schedule/fixed", headers=auth_headers)
    labels = [s.get("label") or s.get("title") for s in list_resp.json()]
    # New label should be present, old ones should be gone
    assert "New" in labels
    assert "Old" not in labels
    assert "Old2" not in labels


async def test_update_nonexistent_slot_returns_404(client: AsyncClient, auth_headers: dict):
    """PUT on a slot that doesn't exist returns 404."""
    resp = await client.put(
        "/api/v1/schedule/slots/99999",
        headers=auth_headers,
        json={"title": "Ghost"},
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_slot_returns_404(client: AsyncClient, auth_headers: dict):
    """DELETE on a slot that doesn't exist returns 404."""
    resp = await client.delete("/api/v1/schedule/slots/99999", headers=auth_headers)
    assert resp.status_code == 404
