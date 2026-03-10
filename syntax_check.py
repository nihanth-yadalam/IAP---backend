import py_compile, sys

files = [
    "app/api/v1/auth.py",
    "app/api/v1/users.py",
    "app/api/v1/courses.py",
    "app/api/v1/tasks.py",
    "app/api/v1/schedule.py",
    "app/api/v1/sync.py",
    "app/api/v1/webhooks.py",
    "app/api/v1/onboarding.py",
    "app/api/v1/admin.py",
    "app/api/v1/router.py",
    "app/models/user.py",
    "app/models/task.py",
    "app/models/schedule.py",
    "app/models/sync.py",
    "app/schemas/user.py",
    "app/core/security.py",
    "app/core/config.py",
    "app/core/utils.py",
    "app/background/scheduler.py",
    "app/services/sync_engine.py",
    "app/services/calendar_service.py",
    "app/services/google_oauth.py",
    "app/main.py",
]

ok = fail = 0
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK    {f}")
        ok += 1
    except py_compile.PyCompileError as e:
        print(f"  FAIL  {f} => {e}")
        fail += 1
    except FileNotFoundError:
        print(f"  MISS  {f} (file not found)")

print(f"\nSyntax check: {ok} OK, {fail} FAILED")
