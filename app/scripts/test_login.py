import asyncio
import httpx
import sys
import subprocess
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1"
EMAIL = "login_test@example.com"
USERNAME = "login_test_user"
PASSWORD = "password123"

async def run_verification():
    print("Starting Login Verification...")
    
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

        # 2. Login with Email
        print("\n[2] Logging In with EMAIL...")
        try:
            resp = await client.post(f"{BASE_URL}/login/access-token", data={
                "username": EMAIL,
                "password": PASSWORD
            })
            if resp.status_code == 200:
                print("SUCCESS: Logged in with EMAIL")
            else:
                print(f"FAIL: Login with EMAIL failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

        # 3. Login with Username
        print("\n[3] Logging In with USERNAME...")
        try:
            resp = await client.post(f"{BASE_URL}/login/access-token", data={
                "username": USERNAME,
                "password": PASSWORD
            })
            if resp.status_code == 200:
                print("SUCCESS: Logged in with USERNAME")
            else:
                print(f"FAIL: Login with USERNAME failed: {resp.status_code} - {resp.text}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

if __name__ == "__main__":
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8001"], # Use different port to avoid conflict
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    try:
        # Update BASE_URL for this run
        globals()['BASE_URL'] = "http://127.0.0.1:8001/api/v1"
        import time
        time.sleep(5)
        asyncio.run(run_verification())
    finally:
        process.terminate()
