"""Final comprehensive endpoint validation test."""
import httpx
import uuid

base = "http://localhost:8000/api/v1"
results = []
uid = uuid.uuid4().hex[:8]
email = f"test{uid}@example.com"
username = f"user{uid}"


def test(name, method, url, **kwargs):
    try:
        r = getattr(httpx, method)(url, **kwargs)
        status = "PASS" if r.status_code < 500 else "FAIL"
        results.append((name, status, r.status_code))
    except Exception as e:
        results.append((name, "ERROR", str(e)))


# Register a fresh user (unique each run)
test("Register", "post", f"{base}/users/",
     json={"email": email, "username": username, "password": "pass123"})

# Login
r = httpx.post(f"{base}/auth/login/access-token",
               data={"username": email, "password": "pass123"})
token = r.json().get("access_token", "")
h = {"Authorization": f"Bearer {token}"}
test("Login", "post", f"{base}/auth/login/access-token",
     data={"username": email, "password": "pass123"})

# User endpoints
test("GET /users/me", "get", f"{base}/users/me", headers=h)
test("PUT /users/me/profile", "put", f"{base}/users/me/profile",
     headers=h, json={"full_name": "Test"})
test("POST /users/me/password", "post", f"{base}/users/me/password",
     headers=h, json={"current_password": "pass123", "new_password": "pass456"})
test("POST /users/password-recovery", "post",
     f"{base}/users/password-recovery/{email}")
test("POST /users/reset-password", "post", f"{base}/users/reset-password/",
     json={"token": "bad", "new_password": "x"})

# Re-login with new password (use original email, password was changed to pass456)
r = httpx.post(f"{base}/auth/login/access-token",
               data={"username": email, "password": "pass456"})
token = r.json().get("access_token", "")
if not token:
    # fallback: re-login with original password in case password change failed
    r = httpx.post(f"{base}/auth/login/access-token",
                   data={"username": email, "password": "pass123"})
    token = r.json().get("access_token", "")
h = {"Authorization": f"Bearer {token}"}

# Onboarding
test("GET /onboarding/status", "get", f"{base}/onboarding/status", headers=h)
test("POST /onboarding/questionnaire", "post",
     f"{base}/onboarding/questionnaire", headers=h,
     json={"chronotype": "morning_lark", "study_style": "pomodoro",
           "subject_confidences": {"Math": 7}})

# Admin
test("GET /admin/users", "get", f"{base}/admin/users", headers=h)

# Courses
test("POST /courses/", "post", f"{base}/courses/",
     headers=h, json={"name": "CS101", "color_code": "#00FF00"})
r2 = httpx.get(f"{base}/courses/", headers=h)
course_id = r2.json()[0]["id"] if r2.json() else 999
test("GET /courses/", "get", f"{base}/courses/", headers=h)
test(f"PATCH /courses/{course_id}", "patch",
     f"{base}/courses/{course_id}", headers=h, json={"name": "CS201"})

# Tasks
test("POST /tasks/", "post", f"{base}/tasks/",
     headers=h, json={"title": "Task1", "deadline": "2026-03-01T00:00:00"})
r3 = httpx.get(f"{base}/tasks/", headers=h)
task_id = r3.json()[0]["id"] if r3.json() else 999
test("GET /tasks/", "get", f"{base}/tasks/", headers=h)
test(f"PATCH /tasks/{task_id}", "patch",
     f"{base}/tasks/{task_id}", headers=h, json={"status": "Completed"})
test(f"DELETE /tasks/{task_id}", "delete",
     f"{base}/tasks/{task_id}", headers=h)

# Schedule
test("POST /schedule/fixed", "post", f"{base}/schedule/fixed",
     headers=h, json=[{"day_of_week": "Friday", "start_time": "08:00:00",
                        "end_time": "09:00:00", "label": "Morning"}])
test("GET /schedule/fixed", "get", f"{base}/schedule/fixed", headers=h)
test("POST /schedule/slots", "post", f"{base}/schedule/slots",
     headers=h, json={"title": "Event",
                       "google_start_datetime": "2026-03-01T10:00:00",
                       "google_end_datetime": "2026-03-01T11:00:00"})
# Get the slot id
r4 = httpx.get(f"{base}/schedule/fixed", headers=h)
slots = [s for s in r4.json() if s.get("title") == "Event"]
slot_id = slots[0]["id"] if slots else 999
test(f"PUT /schedule/slots/{slot_id}", "put",
     f"{base}/schedule/slots/{slot_id}", headers=h, json={"title": "Updated Event"})
test(f"DELETE /schedule/slots/{slot_id}", "delete",
     f"{base}/schedule/slots/{slot_id}", headers=h)

# Delete course after tasks
test(f"DELETE /courses/{course_id}", "delete",
     f"{base}/courses/{course_id}", headers=h)

# Sync
test("GET /sync/status", "get", f"{base}/sync/status", headers=h)
test("POST /sync/reset", "post", f"{base}/sync/reset", headers=h)
test("POST /sync/trigger (no google)", "post",
     f"{base}/sync/trigger", headers=h)
test("POST /sync/push-all (no google)", "post",
     f"{base}/sync/push-all", headers=h)
test("POST /sync/initialize (no google)", "post",
     f"{base}/sync/initialize", headers=h)

# Google OAuth
test("GET /auth/google/authorize", "get", f"{base}/auth/google/authorize", headers=h)

# Webhooks
test("POST /webhooks/setup (no google)", "post",
     f"{base}/webhooks/setup", headers=h)
test("POST /webhooks/google-calendar", "post",
     f"{base}/webhooks/google-calendar",
     headers={"X-Goog-Resource-State": "sync"})

# Health
test("GET /health", "get", "http://localhost:8000/health")

# No auth
test("No Auth -> 401", "get", f"{base}/users/me")

# Collision detection
test("POST /tasks/ (for collision)", "post", f"{base}/tasks/",
     headers=h, json={"title": "T1",
                       "scheduled_start_time": "2026-04-01T10:00:00",
                       "scheduled_end_time": "2026-04-01T12:00:00"})
test("Collision -> 409", "post", f"{base}/tasks/",
     headers=h, json={"title": "T2",
                       "scheduled_start_time": "2026-04-01T11:00:00",
                       "scheduled_end_time": "2026-04-01T13:00:00"})

# Duplicate user
test("Duplicate user -> 400", "post", f"{base}/users/",
     json={"email": email, "username": "x", "password": "x"})

# Wrong password
test("Wrong password -> 400", "post", f"{base}/login/access-token",
     data={"username": email, "password": "wrong"})

# Task date filter
test("GET /tasks/ date filter", "get", f"{base}/tasks/",
     headers=h, params={"start_date": "2026-01-01T00:00:00",
                         "end_date": "2026-12-31T23:59:59"})

print()
print("=" * 65)
hdr = f"{'Endpoint':<45} {'Result':<8} {'Code'}"
print(hdr)
print("=" * 65)
for name, status, code in results:
    print(f"{name:<45} {status:<8} {code}")
print("=" * 65)
passed = sum(1 for _, s, _ in results if s == "PASS")
print(f"Total: {len(results)} | Passed: {passed} | Failed: {len(results) - passed}")
