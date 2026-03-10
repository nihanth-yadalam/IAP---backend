import asyncio
import httpx

BASE = "http://127.0.0.1:8000"
API  = BASE + "/api/v1"
EMAIL = "quickcheck_999@example.com"
PW    = "TestPass123!"

async def run():
    results = []
    token = None

    async with httpx.AsyncClient(timeout=10) as c:

        # 1. Health
        r = await c.get(f"{BASE}/health")
        ok = r.status_code == 200
        results.append(("HEALTH CHECK", ok, r.status_code, r.text[:80]))

        # 2. Register
        r = await c.post(f"{API}/users/", json={
            "email": EMAIL, "password": PW, "username": "quickcheck999"
        })
        ok = r.status_code in (200, 201, 400)  # 400 = already exists = fine
        results.append(("REGISTER", ok, r.status_code, r.text[:80]))

        # 3. Login
        r = await c.post(f"{API}/auth/login/access-token",
                         data={"username": EMAIL, "password": PW})
        ok = r.status_code == 200
        results.append(("LOGIN", ok, r.status_code, r.text[:80]))
        if ok:
            token = r.json().get("access_token")

        if token:
            h = {"Authorization": f"Bearer {token}"}

            # 4. GET /users/me
            r = await c.get(f"{API}/users/me", headers=h)
            results.append(("GET CURRENT USER", r.status_code == 200, r.status_code, r.text[:80]))

            # 5. PUT /users/me/profile
            r = await c.put(f"{API}/users/me/profile", headers=h,
                            json={"full_name": "Quick Check", "major": "CS", "university": "Test U"})
            results.append(("UPDATE PROFILE", r.status_code == 200, r.status_code, r.text[:80]))

            # 6. POST /courses/
            r = await c.post(f"{API}/courses/", headers=h, json={
                "name": "Test Course", "code": "TC101",
                "term": "Spring 2025", "instructor_email": "inst@test.edu"
            })
            ok = r.status_code in (200, 201)
            results.append(("CREATE COURSE", ok, r.status_code, r.text[:80]))

            # 7. GET /courses/
            r = await c.get(f"{API}/courses/", headers=h)
            ok = r.status_code == 200
            detail = f"{len(r.json())} courses" if ok else r.text[:80]
            results.append(("LIST COURSES", ok, r.status_code, detail))

            # 8. POST /tasks/
            r = await c.post(f"{API}/tasks/", headers=h, json={
                "title": "Test Task", "description": "desc", "due_date": "2025-12-31T23:59:59"
            })
            ok = r.status_code in (200, 201)
            results.append(("CREATE TASK", ok, r.status_code, r.text[:80]))

            # 9. GET /tasks/
            r = await c.get(f"{API}/tasks/", headers=h)
            ok = r.status_code == 200
            detail = f"{len(r.json())} tasks" if ok else r.text[:80]
            results.append(("LIST TASKS", ok, r.status_code, detail))

            # 10. POST /schedule/slots
            r = await c.post(f"{API}/schedule/slots", headers=h, json={
                "title": "Study", "google_start_datetime": "2025-12-31T10:00:00",
                "google_end_datetime": "2025-12-31T11:00:00"
            })
            ok = r.status_code in (200, 201)
            results.append(("CREATE SCHEDULE SLOT", ok, r.status_code, r.text[:80]))

            # 11. GET /schedule/fixed
            r = await c.get(f"{API}/schedule/fixed", headers=h)
            results.append(("GET FIXED SCHEDULE", r.status_code == 200, r.status_code, r.text[:80]))

            # 12. GET /onboarding/status
            r = await c.get(f"{API}/onboarding/status", headers=h)
            results.append(("ONBOARDING STATUS", r.status_code == 200, r.status_code, r.text[:80]))

            # 13. GET /sync/status
            r = await c.get(f"{API}/sync/status", headers=h)
            results.append(("SYNC STATUS", r.status_code == 200, r.status_code, r.text[:80]))

    # Print summary
    print("\n" + "="*65)
    print("   BACKEND QUICK CHECK RESULTS")
    print("="*65)
    passed = 0
    failed = 0
    for name, ok, status, detail in results:
        icon = "OK  " if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{icon}] [{status}] {name}")
        if not ok:
            print(f"          => {detail}")
    print("="*65)
    print(f"  {passed} passed / {failed} failed / {len(results)} total")
    print("="*65)

asyncio.run(run())
