from fastapi import APIRouter
from app.api.v1 import auth, users, admin, onboarding, courses, tasks, schedule, sync, webhooks

api_router = APIRouter()

api_router.include_router(auth.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["schedule"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
