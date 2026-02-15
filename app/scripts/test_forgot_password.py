import asyncio
import httpx
import sys
import subprocess
import os
import time
from datetime import datetime, timedelta, timezone
from jose import jwt

# Configuration
BASE_URL = "http://127.0.0.1:8005/api/v1"
EMAIL = "forgot_pwd_test@example.com"
USERNAME = "forgot_pwd_user"
OLD_PASSWORD = "old_password123"
NEW_PASSWORD = "new_password456"

# Must match backend secret
SECRET_KEY = "change_this_secret_key_to_something_secure_for_devchanged123"
ALGORITHM = "HS256"

def generate_test_token(email):
    delta = timedelta(hours=1)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = int(expires.timestamp())
    encoded_jwt = jwt.encode(
        {"exp": exp, "sub": email}, SECRET_KEY, algorithm=ALGORITHM,
    )
    return encoded_jwt

async def run_verification():
    print("Starting Forgot Password Verification...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Register User
        print("\n[1] Registering User...")
        try:
            resp = await client.post(f"{BASE_URL}/users/", json={
                "email": EMAIL,
                "password": OLD_PASSWORD,
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

        # 2. Request Password Recovery (Trigger Server Log)
        print("\n[2] Requesting Password Recovery...")
        try:
            resp = await client.post(f"{BASE_URL}/users/password-recovery/{EMAIL}")
            if resp.status_code == 200:
                print("SUCCESS: Recovery request accepted.")
            else:
                print(f"FAIL: Recovery request failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             return

        # 3. Simulate getting token (since we can't read server stdout easily)
        print("\n[3] Generating Token locally (Verification hack)...")
        token = generate_test_token(EMAIL)
        
        # 4. Reset Password
        print("\n[4] Resetting Password with Token...")
        try:
            resp = await client.post(f"{BASE_URL}/users/reset-password/", json={
                "token": token,
                "new_password": NEW_PASSWORD
            })
            if resp.status_code == 200:
                print("SUCCESS: Password reset successful.")
            else:
                print(f"FAIL: Password reset failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")
             return

        # 5. Login with NEW Password
        print("\n[5] Logging In with NEW Password...")
        try:
            resp = await client.post(f"{BASE_URL}/login/access-token", data={
                "username": USERNAME,
                "password": NEW_PASSWORD
            })
            if resp.status_code == 200:
                print("SUCCESS: Logged in with NEW password.")
            else:
                print(f"FAIL: Login with NEW password failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
             print(f"Request Error: {repr(e)}")

        # 6. Login with OLD Password (Should Fail)
        print("\n[6] Logging In with OLD Password (Should Fail)...")
        try:
            resp = await client.post(f"{BASE_URL}/login/access-token", data={
                "username": USERNAME,
                "password": OLD_PASSWORD
            })
            if resp.status_code == 400:
                print("SUCCESS: Login with OLD password failed as expected.")
            else:
                print(f"FAIL: Unexpected response code: {resp.status_code}")
        except Exception as e:
             print(f"Request Error: {repr(e)}")

if __name__ == "__main__":
    globals()['BASE_URL'] = "http://127.0.0.1:8005/api/v1"
    asyncio.run(run_verification())
