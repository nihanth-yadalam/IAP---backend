import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_sync_status(async_client: AsyncClient, normal_user_token_headers):
    response = await async_client.get(f"{settings.API_V1_STR}/sync/status", headers=normal_user_token_headers)
    assert response.status_code == 200
    content = response.json()
    assert "google_linked" in content
    assert content["google_linked"] is False

@pytest.mark.asyncio
async def test_sync_initialize_no_google(async_client: AsyncClient, normal_user_token_headers):
    # Should fail if not linked
    response = await async_client.post(f"{settings.API_V1_STR}/sync/initialize", headers=normal_user_token_headers)
    assert response.status_code == 400
    assert "Google account not linked" in response.json()["detail"]

@pytest.mark.asyncio
async def test_sync_trigger_no_google(async_client: AsyncClient, normal_user_token_headers):
    response = await async_client.post(f"{settings.API_V1_STR}/sync/trigger", headers=normal_user_token_headers)
    assert response.status_code == 400
    assert "Google account not linked" in response.json()["detail"]

@pytest.mark.asyncio
async def test_sync_reset(async_client: AsyncClient, normal_user_token_headers):
    response = await async_client.post(f"{settings.API_V1_STR}/sync/reset", headers=normal_user_token_headers)
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Sync state reset successfully"
