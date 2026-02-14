"""
Onboarding endpoints — from System A.
M11: GET  /onboarding/status
M12: POST /onboarding/questionnaire
"""

from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.schedule import FixedSlot
from app.schemas.onboarding import OnboardingAnswers

router = APIRouter()


# ── M11 — Onboarding status ──────────────────────────────────────────

@router.get("/status")
async def get_onboarding_status(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Check Onboarding Status.
    Returns step: "questionnaire" | "schedule" | "done".
    """
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if not profile.onboarding_data:
        return {"is_complete": False, "step": "questionnaire"}

    result = await db.execute(select(FixedSlot).where(FixedSlot.user_id == current_user.id))
    if not result.scalars().first():
        return {"is_complete": False, "step": "schedule"}

    return {"is_complete": True, "step": "done"}


# ── M12 — Submit questionnaire ───────────────────────────────────────

@router.post("/questionnaire")
async def submit_questionnaire(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    answers: OnboardingAnswers,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Submit Onboarding Questionnaire."""
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.onboarding_data = answers.model_dump()
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return {"message": "Onboarding questionnaire saved successfully", "step": "schedule"}
