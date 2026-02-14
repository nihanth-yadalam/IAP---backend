import asyncio
import httpx
import sys
import subprocess
import os
import time

# Configuration
BASE_URL = "http://127.0.0.1:8006/api/v1"
EMAIL = "onboarding_test@example.com"
USERNAME = "onboarding_user"
PASSWORD = "password123"

async def run_verification():
    print("Starting Onboarding Verification...")
    
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

        # 3. Check Initial Status
        print("\n[3] Checking Initial Status...")
        try:
            resp = await client.get(f"{BASE_URL}/onboarding/status", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                print(f"Status: {data}")
                if data["is_complete"] == False and data["step"] == "questionnaire":
                     print("SUCCESS: Correct initial status.")
                else:
                     print("FAIL: Incorrect initial status.")
            else:
                print(f"FAIL: Status check failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

        # 4. Submit Questionnaire
        print("\n[4] Submitting Questionnaire...")
        payload = {
            "chronotype": "morning_lark", # Matches Enum
            "study_style": "pomodoro",
            "subject_confidences": {
                "Math": 8,
                "History": 5
            },
            "random_future_question": "answer" # Logic from Requirement: allow extra
        }
        try:
            resp = await client.post(f"{BASE_URL}/onboarding/questionnaire", headers=headers, json=payload)
            if resp.status_code == 200:
                print("SUCCESS: Questionnaire submitted.")
            else:
                print(f"FAIL: Submission failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             return

        # 5. Check Output Status (Intermediate)
        print("\n[5] Checking Status After Questionnaire (Should be 'schedule')...")
        try:
            resp = await client.get(f"{BASE_URL}/onboarding/status", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                print(f"Status: {data}")
                if data["is_complete"] == False and data["step"] == "schedule":
                     print("SUCCESS: Correct intermediate status.")
                else:
                     print("FAIL: Incorrect intermediate status.")
            else:
                print(f"FAIL: Status check failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

        # 6. Add Fixed Slot to complete flow
        print("\n[6] Adding Fixed Slot to complete onboarding...")
        try:
            resp = await client.post(f"{BASE_URL}/schedule/fixed", headers=headers, json=[
                {
                    "day_of_week": "Monday", 
                    "start_time": "09:00:00", 
                    "end_time": "10:00:00", 
                    "label": "Test"
                }
            ])
            if resp.status_code == 200:
                 print("SUCCESS: Slot added.")
            else:
                 print(f"FAIL: Add slot failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

        # 7. Check Final Status
        print("\n[7] Checking Final Status (Should be 'done')...")
        try:
            resp = await client.get(f"{BASE_URL}/onboarding/status", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                print(f"Status: {data}")
                if data["is_complete"] == True and data["step"] == "done":
                     print("SUCCESS: Correct final status.")
                else:
                     print("FAIL: Incorrect final status.")
            else:
                print(f"FAIL: Status check failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

if __name__ == "__main__":
    globals()['BASE_URL'] = "http://127.0.0.1:8006/api/v1"
    asyncio.run(run_verification())
