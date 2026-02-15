import asyncio
import httpx
import sys
import subprocess
import os
import time

# Configuration
BASE_URL = "http://127.0.0.1:8006/api/v1"
EMAIL = "schedule_test@example.com"
USERNAME = "schedule_user"
PASSWORD = "password123"

async def run_verification():
    print("Starting Schedule Verification...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Register User
        print("\n[1] Registering User...")
        try:
            resp = await client.post(f"{BASE_URL}/users/", json={
                "email": EMAIL,
                "password": PASSWORD,
                "username": USERNAME
            })
            if resp.status_code == 200 or (resp.status_code == 400 and "exists" in resp.text):
                print("Registration Successful (or exists)")
            else:
                print(f"Registration Failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             return

        # 2. Login
        print("\n[2] Logging In...")
        token = None
        try:
            resp = await client.post(f"{BASE_URL}/login/access-token", data={
                "username": USERNAME,
                "password": PASSWORD
            })
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                print("Login Successful.")
            else:
                print(f"Login Failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             return

        headers = {"Authorization": f"Bearer {token}"}

        # 3. Add Fixed Slots
        print("\n[3] Adding Fixed Slots...")
        payload = [
            {
                "day_of_week": "Monday",
                "start_time": "09:00:00",
                "end_time": "10:30:00",
                "label": "Chemistry Lab"
            },
            {
                "day_of_week": "Wednesday",
                "start_time": "14:00:00",
                "end_time": "15:30:00",
                "label": "Physics Lecture",
                "is_google_event": False
            }
        ]
        try:
            resp = await client.post(f"{BASE_URL}/schedule/fixed", headers=headers, json=payload)
            if resp.status_code == 200:
                print(f"SUCCESS: {resp.json()}")
            else:
                print(f"FAIL: Add slots failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             return

        # 4. Get Fixed Slots
        print("\n[4] Retrieving Fixed Slots...")
        try:
            resp = await client.get(f"{BASE_URL}/schedule/fixed", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                print(f"Retrieved {len(data)} slots.")
                if len(data) >= 2:
                     print("SUCCESS: Retrieved expected slots.")
                else:
                     print("FAIL: Missing slots.")
            else:
                print(f"FAIL: Get slots failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

if __name__ == "__main__":
    globals()['BASE_URL'] = "http://127.0.0.1:8006/api/v1"
    asyncio.run(run_verification())
