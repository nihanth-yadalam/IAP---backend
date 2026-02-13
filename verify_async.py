import asyncio
import sys
import os
import random
import string
import traceback
from httpx import AsyncClient, ASGITransport
import bcrypt

# Monkeypatch bcrypt for passlib compatibility (bcrypt 4.1.0+ removed __about__)
if not hasattr(bcrypt, '__about__'):
    class About:
        __version__ = bcrypt.__version__
    bcrypt.__about__ = About()

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.main import app

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))

async def run_verification():
    print("--- Starting Async Verification for Epic 3.1 ---")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        
        # 0. Health Check
        print("\n[0] Health Check (Root Endpoint)...")
        r = await client.get("/")
        print(f"Root endpoint status: {r.status_code}")
        if r.status_code != 200:
            print(f"Failed: {r.text}")
            return

        # 1. Setup User
        email = f"test_{random_string()}@example.com"
        password = "password123"
        username = f"user_{random_string()}"
        
        print(f"\n[1] Creating User: {email}")
        r = await client.post("/api/v1/users/", json={
            "email": email,
            "password": password,
            "username": username
        })
        if r.status_code != 200:
            print(f"Failed to create user: {r.text}")
            return
        user_id = r.json()["id"]
        print("User created successfully.")

        # 2. Login
        print("\n[2] Logging in...")
        r = await client.post("/api/v1/login/access-token", data={
            "username": email,
            "password": password
        })
        if r.status_code != 200:
            print(f"Login failed: {r.text}")
            return
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Logged in successfully.")

        # 3. Create Course
        print("\n[3] Creating Course 'Math'...")
        r = await client.post("/api/v1/courses/", json={
            "name": "Math",
            "color_code": "#FF0000"
        }, headers=headers)
        if r.status_code != 200:
            print(f"Failed to create course: {r.text}")
            return
        course_id = r.json()["id"]
        print(f"Course created: ID {course_id}")

        # 4. Create Task (Manual - Success)
        print("\n[4] Creating Manual Task (Valid)...")
        task_data = {
            "title": "Study Math",
            "course_id": course_id,
            "priority": "High",
            "scheduled_start_time": "2026-02-12T10:00:00",
            "scheduled_end_time": "2026-02-12T11:00:00",
            "category": "Study"
        }
        r = await client.post("/api/v1/tasks/", json=task_data, headers=headers)
        if r.status_code != 200:
             print(f"Failed to create task: {r.text}")
        else:
             print(f"Task created successfully: {r.json()['id']}")

        # 5. Create Task (Collision - Task vs Task)
        print("\n[5] Creating Conflicting Task (Expect 409)...")
        conflict_data = {
            "title": "Exam Prep",
            "priority": "Medium",
            "scheduled_start_time": "2026-02-12T10:30:00",
            "scheduled_end_time": "2026-02-12T11:30:00",
            "category": "Exam"
        }
        r = await client.post("/api/v1/tasks/", json=conflict_data, headers=headers)
        if r.status_code == 409:
            print("SUCCESS: Got 409 Conflict.")
        else:
            print(f"FAILURE: Expected 409, got {r.status_code} - {r.text}")

        # 6. Validation Error
        print("\n[6] Creating Task Missing End Time (Expect 422)...")
        invalid_data = {
            "title": "Invalid Task",
            "scheduled_start_time": "2026-02-12T12:00:00"
        }
        r = await client.post("/api/v1/tasks/", json=invalid_data, headers=headers)
        if r.status_code == 422:
            print("SUCCESS: Got 422 Validation Error.")
        else:
             print(f"FAILURE: Expected 422, got {r.status_code} - {r.text}")

        # 7. Fixed Slot Setup
        print("\n[7] Creating Fixed Slot (Friday)...")
        fixed_data = [{
            "day_of_week": "Friday",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "label": "Class",
            "is_google_event": False
        }]
        r = await client.post("/api/v1/schedule/fixed", json=fixed_data, headers=headers)
        if r.status_code != 200:
             print(f"Failed to create fixed slot: {r.text}")
        else:
             print("Fixed slot created.")

        # 8. Fixed Slot Collision
        print("\n[8] Creating Task Conflicting Fixed Slot (Friday)...")
        conflict_fixed = {
            "title": "Project Meeting",
            "scheduled_start_time": "2026-02-13T10:30:00", # Friday
            "scheduled_end_time": "2026-02-13T11:30:00",
            "category": "Project"
        }
        r = await client.post("/api/v1/tasks/", json=conflict_fixed, headers=headers)
        if r.status_code == 409:
             print("SUCCESS: Got 409 Conflict.")
        else:
             print(f"FAILURE: Expected 409, got {r.status_code} - {r.text}")

if __name__ == "__main__":
    try:
        asyncio.run(run_verification())
    except Exception:
        traceback.print_exc()
