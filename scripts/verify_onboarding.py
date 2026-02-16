import asyncio
import httpx
import sys
import subprocess
import os
import time

# Configuration
BASE_URL = "http://127.0.0.1:8006/api/v1"
EMAIL = "onboarding_test_v2@example.com"
USERNAME = "onboarding_user_v2"
PASSWORD = "password123"

async def run_verification():
    print("Starting Onboarding Verification V2...")
    
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
            resp = await client.post(f"{BASE_URL}/auth/login/access-token", data={
                "username": USERNAME,
                "password": PASSWORD
            })
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                print("Login Successful.")
            else:
                print(f"Login Failed: {resp.status_code} - {resp.json()}")
                print(f"URL: {BASE_URL}/auth/login/access-token")
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
                # Expect questionnaire or schedule depending on run
                if data["step"] in ["questionnaire", "schedule", "done"]:
                     print(f"SUCCESS: Initial status is {data['step']}")
                else:
                     print("FAIL: Incorrect initial status.")
            else:
                print(f"FAIL: Status check failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

        # 4. Submit Questionnaire (New Payload)
        print("\n[4] Submitting Questionnaire...")
        payload = {
            "name": "Alex Smith",
            "university": "Stanford University",
            "major": "Computer Science",
            "chronotype": "morning",
            "work_style": "deep",
            "preferred_session_mins": 60
        }
        try:
            resp = await client.post(f"{BASE_URL}/onboarding/questionnaire", headers=headers, json=payload)
            if resp.status_code == 200:
                print("SUCCESS: Questionnaire submitted.")
            else:
                print(f"FAIL: Submission failed: {resp.status_code} - {resp.text}")
                # Proceeding to check if it was already submitted? 
                # If already done, might be fine.
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             return

        # 4.5 Verify Profile Update
        print("\n[4.5] Verifying Profile Update...")
        try:
            resp = await client.get(f"{BASE_URL}/users/me", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # Debug print
                # print(data)
                if (data.get("full_name") == "Alex Smith" and 
                    data.get("university") == "Stanford University" and
                    data.get("major") == "Computer Science"):
                     print("SUCCESS: Profile fields updated correctly.")
                else:
                     print(f"FAIL: Profile mismatch: Name={data.get('full_name')}, Uni={data.get('university')}, Major={data.get('major')}")
            else:
                print(f"FAIL: Profile check failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

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
                    # If we ran this test before, we might have slots already?
                     print(f"Intermediate status: {data['step']}")
            else:
                print(f"FAIL: Status check failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

if __name__ == "__main__":
    globals()['BASE_URL'] = "http://127.0.0.1:8006/api/v1"
    asyncio.run(run_verification())
