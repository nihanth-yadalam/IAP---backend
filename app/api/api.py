from fastapi import APIRouter
from app.api.endpoints import auth, users, onboarding, schedule

api_router = APIRouter()
api_router.include_router(auth.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["schedule"])
