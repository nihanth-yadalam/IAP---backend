import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_create_course(async_client: AsyncClient, normal_user_token_headers):
    data = {"name": "Test Course", "color_code": "#FF0000"}
    response = await async_client.post(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers, json=data)
    assert response.status_code == 200
    content = response.json()
    assert content["name"] == data["name"]
    assert "id" in content

@pytest.mark.asyncio
async def test_read_courses(async_client: AsyncClient, normal_user_token_headers):
    # Ensure at least one course exists
    data = {"name": "Read Course", "color_code": "#00FF00"}
    await async_client.post(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers, json=data)
    
    response = await async_client.get(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers)
    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert len(content) >= 1

@pytest.mark.asyncio
async def test_update_course(async_client: AsyncClient, normal_user_token_headers):
    # Create
    data = {"name": "Update Course", "color_code": "#0000FF"}
    create_res = await async_client.post(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers, json=data)
    course_id = create_res.json()["id"]
    
    # Update
    update_data = {"name": "Updated Course Name"}
    response = await async_client.patch(f"{settings.API_V1_STR}/courses/{course_id}", headers=normal_user_token_headers, json=update_data)
    assert response.status_code == 200
    content = response.json()
    assert content["name"] == "Updated Course Name"

@pytest.mark.asyncio
async def test_delete_course(async_client: AsyncClient, normal_user_token_headers):
    # Create
    data = {"name": "Delete Course", "color_code": "#FFFF00"}
    create_res = await async_client.post(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers, json=data)
    course_id = create_res.json()["id"]
    
    # Delete
    response = await async_client.delete(f"{settings.API_V1_STR}/courses/{course_id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    
    # Verify
    get_res = await async_client.get(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers)
    courses = get_res.json()
    assert not any(c["id"] == course_id for c in courses)
