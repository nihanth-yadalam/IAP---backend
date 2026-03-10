#!/usr/bin/env python
"""
Runtime API verification script - tests all major endpoints
"""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_EMAIL = f"test_{int(datetime.now().timestamp())}@example.com"
TEST_PASSWORD = "TestPassword123!"
TEST_USERNAME = "testuser"

async def test_health_check():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("[1] Testing Health Check")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get("http://127.0.0.1:8000/health")
            print(f"✓ Status: {resp.status_code}")
            print(f"✓ Response: {resp.json()}")
            return True
        except Exception as e:
            print(f"✗ Error: {e}")
            return False

async def test_user_registration():
    """Test user registration"""
    print("\n" + "="*60)
    print("[2] Testing User Registration")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(f"{BASE_URL}/users/", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "username": TEST_USERNAME
            })
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ User Created: {data.get('email')}")
                return True
            elif resp.status_code == 400 and "already exists" in resp.text:
                print(f"✓ User Already Exists (expected)")
                return True
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False

async def test_user_login():
    """Test user login"""
    print("\n" + "="*60)
    print("[3] Testing User Login")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(f"{BASE_URL}/auth/login/access-token", data={
                "username": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                print(f"✓ Login Successful")
                print(f"✓ Token Type: {data.get('token_type')}")
                return token
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None

async def test_get_user_profile(token):
    """Test get current user profile"""
    print("\n" + "="*60)
    print("[4] Testing Get User Profile")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.get(f"{BASE_URL}/users/me", headers=headers)
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ Email: {data.get('email')}")
                print(f"✓ Username: {data.get('username')}")
                print(f"✓ Has Profile: {'profile' in data and data['profile'] is not None}")
                return True
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False

async def test_update_user_profile(token):
    """Test update user profile"""
    print("\n" + "="*60)
    print("[5] Testing Update User Profile")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.put(f"{BASE_URL}/users/me/profile", headers=headers, json={
                "full_name": "Test User",
                "major": "Computer Science",
                "university": "Test University"
            })
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"✓ Profile Updated Successfully")
                return True
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False

async def test_create_course(token):
    """Test create course"""
    print("\n" + "="*60)
    print("[6] Testing Create Course")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(f"{BASE_URL}/courses/", headers=headers, json={
                "name": "Test Course",
                "code": "CS101",
                "term": "Spring 2024",
                "instructor_email": "instructor@university.edu"
            })
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                course_id = data.get("id")
                print(f"✓ Course Created: {data.get('name')}")
                print(f"✓ Course ID: {course_id}")
                return course_id
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None

async def test_list_courses(token):
    """Test list courses"""
    print("\n" + "="*60)
    print("[7] Testing List Courses")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.get(f"{BASE_URL}/courses/", headers=headers)
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ Courses Retrieved: {len(data)} courses found")
                return True
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False

async def test_create_task(token):
    """Test create task"""
    print("\n" + "="*60)
    print("[8] Testing Create Task")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(f"{BASE_URL}/tasks/", headers=headers, json={
                "title": "Test Task",
                "description": "This is a test task",
                "due_date": "2024-12-31T23:59:59"
            })
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                task_id = data.get("id")
                print(f"✓ Task Created: {data.get('title')}")
                print(f"✓ Task ID: {task_id}")
                return task_id
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None

async def test_list_tasks(token):
    """Test list tasks"""
    print("\n" + "="*60)
    print("[9] Testing List Tasks")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.get(f"{BASE_URL}/tasks/", headers=headers)
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ Tasks Retrieved: {len(data)} tasks found")
                return True
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False

async def test_create_schedule_slot(token):
    """Test create schedule slot"""
    print("\n" + "="*60)
    print("[10] Testing Create Schedule Slot")
    print("="*60)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(f"{BASE_URL}/schedule/slots", headers=headers, json={
                "title": "Study Session",
                "google_start_datetime": "2024-12-31T10:00:00",
                "google_end_datetime": "2024-12-31T11:00:00"
            })
            print(f"✓ Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                slot_id = data.get("id")
                print(f"✓ Slot Created: {data.get('title')}")
                print(f"✓ Slot ID: {slot_id}")
                return slot_id
            else:
                print(f"✗ Error: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None

async def main():
    """Run all tests"""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║        BACKEND API RUNTIME VERIFICATION TEST SUITE         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Email: {TEST_EMAIL}")

    results = {}

    # Test health check
    results["health_check"] = await test_health_check()

    # Test registration
    results["registration"] = await test_user_registration()

    if results["registration"]:
        # Test login
        token = await test_user_login()
        results["login"] = token is not None

        if token:
            # Test authenticated endpoints
            results["get_profile"] = await test_get_user_profile(token)
            results["update_profile"] = await test_update_user_profile(token)
            results["create_course"] = await test_create_course(token) is not None
            results["list_courses"] = await test_list_courses(token)
            results["create_task"] = await test_create_task(token) is not None
            results["list_tasks"] = await test_list_tasks(token)
            results["create_schedule_slot"] = await test_create_schedule_slot(token) is not None

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print("="*60)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    asyncio.run(main())
