import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_create_fixed_slot(async_client: AsyncClient, normal_user_token_headers):
    data = [{
        "day_of_week": "Monday",
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "label": "Class",
        "is_google_event": False
    }]
    response = await async_client.post(f"{settings.API_V1_STR}/schedule/fixed", headers=normal_user_token_headers, json=data)
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert content[0]["label"] == "Class"

@pytest.mark.asyncio
async def test_read_fixed_slots(async_client: AsyncClient, normal_user_token_headers):
    response = await async_client.get(f"{settings.API_V1_STR}/schedule/fixed", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_delete_fixed_slot(async_client: AsyncClient, normal_user_token_headers):
    # Create
    data = [{
        "day_of_week": "Tuesday",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "label": "Lab"
    }]
    res = await async_client.post(f"{settings.API_V1_STR}/schedule/fixed", headers=normal_user_token_headers, json=data)
    slot_id = res.json()[0]["id"]
    
    # Delete
    response = await async_client.delete(f"{settings.API_V1_STR}/schedule/slots/{slot_id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    
    # Verify
    get_res = await async_client.get(f"{settings.API_V1_STR}/schedule/fixed", headers=normal_user_token_headers)
    assert not any(s["id"] == slot_id for s in get_res.json())
