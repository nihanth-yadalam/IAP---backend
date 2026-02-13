import sys
import os
import random
import string
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.main import app

client = TestClient(app)

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))

def run_verification():
    print("--- Starting Verification for Epic 3.1 (Manual Task Entry) ---")

    # 0. Health Check
    print("\n[0] Health Check (Root Endpoint)...")
    try:
        r = client.get("/")
        print(f"Root endpoint status: {r.status_code}")
        if r.status_code == 200:
            print("Root endpoint accessible.")
        else:
            print(f"Root endpoint failed: {r.text}")
    except Exception as e:
        print(f"Root endpoint exception: {e}")
        return

    # 1. Setup User
    email = f"test_{random_string()}@example.com"
    password = "password123"
    username = f"user_{random_string()}"
    
    print(f"\n[1] Creating User: {email}")
    r = client.post("/api/v1/users/", json={
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
    r = client.post("/api/v1/login/access-token", data={
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
    r = client.post("/api/v1/courses/", json={
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
    r = client.post("/api/v1/tasks/", json=task_data, headers=headers)
    if r.status_code != 200:
        print(f"Failed to create task: {r.text}")
    else:
        print(f"Task created successfully: {r.json()['id']}")

    # 5. Create Task (Collision - Task vs Task)
    print("\n[5] Creating Conflicting Task (Expect 409)...")
    conflict_data = {
        "title": "Exam Prep",
        "priority": "Medium",
        "scheduled_start_time": "2026-02-12T10:30:00",  # Overlaps 10:00-11:00
        "scheduled_end_time": "2026-02-12T11:30:00",
        "category": "Exam"
    }
    r = client.post("/api/v1/tasks/", json=conflict_data, headers=headers)
    if r.status_code == 409:
        print("SUCCESS: Got 409 Conflict as expected.")
        print(f"Message: {r.json()['detail']}")
    else:
        print(f"FAILURE: Expected 409, got {r.status_code} - {r.text}")

    # 6. Create Task (Validation Error - Missing End Time)
    print("\n[6] Creating Task with Missing End Time (Expect 422)...")
    invalid_data = {
        "title": "Invalid Task",
        "scheduled_start_time": "2026-02-12T12:00:00"
        # Missing scheduled_end_time
    }
    r = client.post("/api/v1/tasks/", json=invalid_data, headers=headers)
    if r.status_code == 422:
        print("SUCCESS: Got 422 Validation Error as expected.")
    else:
        print(f"FAILURE: Expected 422, got {r.status_code} - {r.text}")

    # 7. Create Fixed Slot
    print("\n[7] Creating Fixed Slot (Friday 10:00-11:00)...")
    # Note: FixedSlot API expects day_of_week enum.
    fixed_data = [{
        "day_of_week": "Friday",
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "label": "Class",
        "is_google_event": False
    }]
    r = client.post("/api/v1/schedule/fixed", json=fixed_data, headers=headers)
    if r.status_code != 200:
        print(f"Failed to create fixed slot: {r.text}")
    else:
        print("Fixed slot created.")

    # 8. Create Task (Collision - Task vs Fixed Slot)
    print("\n[8] Creating Task Conflicting with Fixed Slot (Expect 409)...")
    # Friday is 2026-02-13
    conflict_fixed_data = {
        "title": "Club Meeting",
        "scheduled_start_time": "2026-02-13T10:30:00", # Friday
        "scheduled_end_time": "2026-02-13T11:30:00",
        "category": "Assignment"
    }
    r = client.post("/api/v1/tasks/", json=conflict_fixed_data, headers=headers)
    if r.status_code == 409:
        print("SUCCESS: Got 409 Conflict as expected.")
        print(f"Message: {r.json()['detail']}")
    else:
        print(f"FAILURE: Expected 409, got {r.status_code} - {r.text}")
        
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    import traceback
    try:
        run_verification()
    except Exception:
        traceback.print_exc()
