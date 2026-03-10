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
from app.services.memory_utils import initialize_memory

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

    # Update Profile fields
    if answers.name:
        profile.full_name = answers.name
    if answers.university:
        profile.university = answers.university
    if answers.major:
        profile.major = answers.major

    # Update onboarding_data (excluding profile fields)
    onboarding_payload = answers.model_dump(exclude={"name", "university", "major"})
    profile.onboarding_data = onboarding_payload
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    # Initialize AI memory structure in onboarding_data JSONB
    # Map chronotype to memory format
    chrono_map = {"morning": "early_bird", "night": "night_owl", "balanced": "balanced"}
    chronotype = chrono_map.get(answers.chronotype.value, "balanced")
    preferred_session_mins = answers.preferred_session_mins

    await initialize_memory(
        db=db,
        user_id=current_user.id,
        chronotype=chronotype,
        base_energy_level=7,  # default; not asked during onboarding
        preferred_session_duration_mins=preferred_session_mins,
    )
    await db.commit()

    return {"message": "Onboarding questionnaire saved successfully", "step": "schedule"}
