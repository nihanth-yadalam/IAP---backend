import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from app.core.config import settings

@pytest.mark.asyncio
async def test_create_task(async_client: AsyncClient, normal_user_token_headers):
    # Create a course first
    course_data = {"name": "Task Course", "color_code": "#00FFFF"}
    c_res = await async_client.post(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers, json=course_data)
    course_id = c_res.json()["id"]
    
    start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end_time = (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat()
    
    task_data = {
        "title": "Test Task",
        "course_id": course_id,
        "priority": "High",
        "category": "Study",
        "scheduled_start_time": start_time,
        "scheduled_end_time": end_time
    }
    
    response = await async_client.post(f"{settings.API_V1_STR}/tasks/", headers=normal_user_token_headers, json=task_data)
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == "Test Task"
    assert content["course_id"] == course_id

@pytest.mark.asyncio
async def test_create_task_collision(async_client: AsyncClient, normal_user_token_headers):
    # Create a course
    course_data = {"name": "Collision Course", "color_code": "#FF00FF"}
    c_res = await async_client.post(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers, json=course_data)
    course_id = c_res.json()["id"]
    
    base_time = datetime.utcnow() + timedelta(days=2)
    start_time = base_time.isoformat()
    end_time = (base_time + timedelta(hours=2)).isoformat()
    
    # Task 1
    task1_data = {
        "title": "Task 1",
        "course_id": course_id,
        "scheduled_start_time": start_time,
        "scheduled_end_time": end_time,
        "priority": "Medium",
        "category": "Assignment"
    }
    await async_client.post(f"{settings.API_V1_STR}/tasks/", headers=normal_user_token_headers, json=task1_data)
    
    # Task 2 (Overlapping)
    overlap_start = (base_time + timedelta(hours=1)).isoformat() # Starts in middle of Task 1
    overlap_end = (base_time + timedelta(hours=3)).isoformat()
    
    task2_data = {
        "title": "Task 2 Collision",
        "course_id": course_id,
        "scheduled_start_time": overlap_start,
        "scheduled_end_time": overlap_end,
        "priority": "Low",
        "category": "Revision"
    }
    
    response = await async_client.post(f"{settings.API_V1_STR}/tasks/", headers=normal_user_token_headers, json=task2_data)
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_read_tasks(async_client: AsyncClient, normal_user_token_headers):
    response = await async_client.get(f"{settings.API_V1_STR}/tasks/", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_update_task(async_client: AsyncClient, normal_user_token_headers):
    # Create valid task
    course_data = {"name": "Update Task Course", "color_code": "#123456"}
    c_res = await async_client.post(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers, json=course_data)
    course_id = c_res.json()["id"]
    
    start = (datetime.utcnow() + timedelta(days=10)).isoformat()
    end = (datetime.utcnow() + timedelta(days=10, hours=1)).isoformat()
    
    task_data = {
        "title": "Original Title",
        "course_id": course_id,
        "scheduled_start_time": start,
        "scheduled_end_time": end,
        "priority": "Low"
    }
    create_res = await async_client.post(f"{settings.API_V1_STR}/tasks/", headers=normal_user_token_headers, json=task_data)
    task_id = create_res.json()["id"]
    
    # Update
    update_data = {"title": "Updated Title"}
    response = await async_client.patch(f"{settings.API_V1_STR}/tasks/{task_id}", headers=normal_user_token_headers, json=update_data)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"

@pytest.mark.asyncio
async def test_delete_task(async_client: AsyncClient, normal_user_token_headers):
    # Create valid task
    course_data = {"name": "Delete Task Course", "color_code": "#654321"}
    c_res = await async_client.post(f"{settings.API_V1_STR}/courses/", headers=normal_user_token_headers, json=course_data)
    course_id = c_res.json()["id"]
    
    start = (datetime.utcnow() + timedelta(days=20)).isoformat()
    end = (datetime.utcnow() + timedelta(days=20, hours=1)).isoformat()
    
    task_data = {
        "title": "Task to Delete",
        "course_id": course_id,
        "scheduled_start_time": start,
        "scheduled_end_time": end,
        "priority": "Low"
    }
    create_res = await async_client.post(f"{settings.API_V1_STR}/tasks/", headers=normal_user_token_headers, json=task_data)
    task_id = create_res.json()["id"]
    
    # Delete
    response = await async_client.delete(f"{settings.API_V1_STR}/tasks/{task_id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    
    # Verify
    get_res = await async_client.get(f"{settings.API_V1_STR}/tasks/", headers=normal_user_token_headers)
    assert not any(t["id"] == task_id for t in get_res.json())
