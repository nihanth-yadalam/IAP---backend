"""
Diagnostic test script - checks all major endpoints
"""
import asyncio
import httpx
import sys

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"

async def main():
    results = {}
    token = None
    
    async with httpx.AsyncClient(timeout=10) as c:
        # 1. Health check
        try:
            r = await c.get(f"{BASE}/health")
            ok = r.status_code == 200
            results["health_check"] = (ok, r.status_code, r.json() if ok else r.text[:100])
        except Exception as e:
            results["health_check"] = (False, None, str(e))

        # 2. Register
        try:
            r = await c.post(f"{API}/users/", json={
                "email": "diagtest@example.com",
                "password": "TestPass123!",
                "username": "diaguser"
            })
            ok = r.status_code in (200, 201, 400)  # 400 = already exists
            results["register"] = (ok, r.status_code, r.text[:200])
        except Exception as e:
            results["register"] = (False, None, str(e))

        # 3. Login (auth router - /auth/login)
        try:
            r = await c.post(f"{API}/auth/login", data={
                "username": "diagtest@example.com",
                "password": "TestPass123!"
            })
            ok = r.status_code == 200
            if ok:
                token = r.json().get("access_token")
            results["login_auth"] = (ok, r.status_code, r.json() if ok else r.text[:200])
        except Exception as e:
            results["login_auth"] = (False, None, str(e))
        
        # 4. Login (legacy /login/access-token if it exists)
        try:
            r = await c.post(f"{API}/login/access-token", data={
                "username": "diagtest@example.com",
                "password": "TestPass123!"
            })
            ok = r.status_code == 200
            if ok and not token:
                token = r.json().get("access_token")
            results["login_access_token"] = (ok, r.status_code, r.json() if ok else r.text[:200])
        except Exception as e:
            results["login_access_token"] = (False, None, str(e))

        if token:
            headers = {"Authorization": f"Bearer {token}"}
            
            # 5. Get current user
            try:
                r = await c.get(f"{API}/users/me", headers=headers)
                ok = r.status_code == 200
                results["get_user_me"] = (ok, r.status_code, r.json() if ok else r.text[:200])
            except Exception as e:
                results["get_user_me"] = (False, None, str(e))

            # 6. Update profile
            try:
                r = await c.put(f"{API}/users/me/profile", headers=headers, json={
                    "full_name": "Diag User",
                    "major": "Computer Science",
                    "university": "Test University"
                })
                ok = r.status_code == 200
                results["update_profile"] = (ok, r.status_code, r.json() if ok else r.text[:200])
            except Exception as e:
                results["update_profile"] = (False, None, str(e))

            # 7. Create course
            course_id = None
            try:
                r = await c.post(f"{API}/courses/", headers=headers, json={
                    "name": "Diag Course",
                    "code": "DIAG101",
                    "term": "Spring 2024",
                    "instructor_email": "instructor@test.edu"
                })
                ok = r.status_code in (200, 201)
                if ok:
                    course_id = r.json().get("id")
                results["create_course"] = (ok, r.status_code, r.json() if ok else r.text[:200])
            except Exception as e:
                results["create_course"] = (False, None, str(e))

            # 8. List courses
            try:
                r = await c.get(f"{API}/courses/", headers=headers)
                ok = r.status_code == 200
                results["list_courses"] = (ok, r.status_code, f"{len(r.json())} courses" if ok else r.text[:200])
            except Exception as e:
                results["list_courses"] = (False, None, str(e))

            # 9. Create task
            task_id = None
            try:
                r = await c.post(f"{API}/tasks/", headers=headers, json={
                    "title": "Diag Task",
                    "description": "Diagnostic test task",
                    "due_date": "2025-12-31T23:59:59"
                })
                ok = r.status_code in (200, 201)
                if ok:
                    task_id = r.json().get("id")
                results["create_task"] = (ok, r.status_code, r.json() if ok else r.text[:200])
            except Exception as e:
                results["create_task"] = (False, None, str(e))

            # 10. List tasks
            try:
                r = await c.get(f"{API}/tasks/", headers=headers)
                ok = r.status_code == 200
                results["list_tasks"] = (ok, r.status_code, f"{len(r.json())} tasks" if ok else r.text[:200])
            except Exception as e:
                results["list_tasks"] = (False, None, str(e))

            # 11. Create schedule slot
            try:
                r = await c.post(f"{API}/schedule/slots", headers=headers, json={
                    "title": "Study Session",
                    "google_start_datetime": "2025-12-31T10:00:00",
                    "google_end_datetime": "2025-12-31T11:00:00"
                })
                ok = r.status_code in (200, 201)
                results["create_schedule_slot"] = (ok, r.status_code, r.json() if ok else r.text[:200])
            except Exception as e:
                results["create_schedule_slot"] = (False, None, str(e))

            # 12. List schedule slots
            try:
                r = await c.get(f"{API}/schedule/slots", headers=headers)
                ok = r.status_code == 200
                results["list_schedule_slots"] = (ok, r.status_code, f"{len(r.json())} slots" if ok else r.text[:200])
            except Exception as e:
                results["list_schedule_slots"] = (False, None, str(e))

            # 13. Onboarding status
            try:
                r = await c.get(f"{API}/onboarding/status", headers=headers)
                ok = r.status_code == 200
                results["onboarding_status"] = (ok, r.status_code, r.json() if ok else r.text[:200])
            except Exception as e:
                results["onboarding_status"] = (False, None, str(e))
        else:
            print("WARNING: Could not obtain auth token. Skipping authenticated tests.")

    # Print results
    print("\n" + "="*70)
    print("  BACKEND DIAGNOSTIC RESULTS")
    print("="*70)
    passed = 0
    failed = 0
    for name, (ok, status, detail) in results.items():
        icon = "✓ PASS" if ok else "✗ FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  {icon}  [{status}] {name}")
        if not ok:
            print(f"         Detail: {detail}")
    
    print("="*70)
    print(f"  Results: {passed} passed, {failed} failed out of {len(results)} tests")
    print("="*70)
    
    if failed > 0:
        sys.exit(1)

asyncio.run(main())
