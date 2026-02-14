import asyncio
import httpx
import sys
import time
import subprocess
import os
from typing import Optional

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"
EMAIL = "test_user@example.com"
PASSWORD = "password123"
USERNAME = "testuser"

async def run_verification():
    print("Starting verification process...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health Check
        print("\n[1] Checking API Health...")
        try:
            resp = await client.get("http://127.0.0.1:8000/")
            print(f"Status: {resp.status_code}, Response: {resp.json()}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            return

        # 2. Register User
        print("\n[2] Registering User...")
        try:
            resp = await client.post(f"{BASE_URL}/users/", json={
                "email": EMAIL,
                "password": PASSWORD,
                "username": USERNAME
            })
            if resp.status_code == 200:
                print("Registration Successful")
            elif resp.status_code == 400 and "already exists" in resp.text:
                 print("User already exists (Expected if re-running)")
            else:
                print(f"Registration Failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             import traceback
             traceback.print_exc()
             return

        # 3. Login
        print("\n[3] Logging In...")
        token = None
        try:
            resp = await client.post(f"{BASE_URL}/login/access-token", data={
                "username": EMAIL,
                "password": PASSWORD
            })
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                print("Login Successful. Token received.")
            else:
                print(f"Login Failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             import traceback
             traceback.print_exc()
             return

        # 4. Get Current User (Protected)
        print("\n[4] Getting Current User Profile...")
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = await client.get(f"{BASE_URL}/users/me", headers=headers)
            if resp.status_code == 200:
                user_data = resp.json()
                print(f"User Data Retrieved: {user_data['email']}")
                print(f"Profile: {user_data.get('profile')}")
            else:
                print(f"Get User Failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             import traceback
             traceback.print_exc()
             return

        # 5. Update Profile
        print("\n[5] Updating Profile...")
        try:
            resp = await client.put(f"{BASE_URL}/users/me/profile", headers=headers, json={
                "full_name": "Test User Updated",
                "major": "Computer Science",
                "university": "Tech University"
            })
            if resp.status_code == 200:
                print("Profile Update Successful")
                print(f"Updated Data: {resp.json()}")
            else:
                print(f"Profile Update Failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             import traceback
             traceback.print_exc()
             return

    print("\nVerification Complete!")

if __name__ == "__main__":
    # Start the server in a subprocess
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    try:
        print("Waiting for server to start...")
        time.sleep(5) # Give it time to start
        asyncio.run(run_verification())
    finally:
        print("\nStopping server...")
        process.terminate()
        process.wait()
