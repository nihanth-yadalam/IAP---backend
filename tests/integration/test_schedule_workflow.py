"""
Integration test: Schedule workflow.

Create fixed slots → Read them → Delete a slot → Verify deletion.
"""

import pytest
from httpx import AsyncClient
from app.core.config import settings

API = settings.API_V1_STR


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schedule_slot_lifecycle(async_client: AsyncClient, normal_user_token_headers: dict):
    """Create fixed slots, read them, delete one, verify."""
    headers = normal_user_token_headers

    # ── 1. Create fixed slots ────────────────────────────────────────
    slots_data = [
        {
            "day_of_week": "Wednesday",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "label": "Integ Lecture",
        },
        {
            "day_of_week": "Wednesday",
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "label": "Integ Lab",
        },
    ]
    r = await async_client.post(f"{API}/schedule/fixed", headers=headers, json=slots_data)
    assert r.status_code == 200, f"Create slots failed: {r.text}"

    # ── 2. Read fixed slots ──────────────────────────────────────────
    r = await async_client.get(f"{API}/schedule/fixed", headers=headers)
    assert r.status_code == 200
    slots = r.json()
    assert isinstance(slots, list)
    assert len(slots) >= 2  # At least the 2 we created

    # Find our "Integ Lab" slot
    lab_slots = [s for s in slots if s.get("label") == "Integ Lab"]
    assert len(lab_slots) >= 1, "Integ Lab slot not found"
    lab_slot_id = lab_slots[0]["id"]

    # ── 3. Delete a slot ─────────────────────────────────────────────
    r = await async_client.delete(f"{API}/schedule/slots/{lab_slot_id}", headers=headers)
    assert r.status_code == 200, f"Delete slot failed: {r.text}"

    # ── 4. Verify deletion ───────────────────────────────────────────
    r = await async_client.get(f"{API}/schedule/fixed", headers=headers)
    assert r.status_code == 200
    remaining = r.json()
    assert not any(s["id"] == lab_slot_id for s in remaining), "Deleted slot still present"
