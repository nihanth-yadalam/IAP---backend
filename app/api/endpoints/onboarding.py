from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.onboarding import OnboardingAnswers

router = APIRouter()

@router.get("/status", response_model=Any)
async def get_onboarding_status(
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Check Onboarding Status
    Story 2.1: Return {"is_complete": bool, "step": ...}
    """
    # Use current_user.profile which is eager loaded
    profile = current_user.profile
    if not profile:
        # Should not happen if registration works correctly
        raise HTTPException(status_code=404, detail="Profile not found")

    onboarding_data = profile.onboarding_data
    is_complete = bool(onboarding_data)
    
    step = "done" if is_complete else "questionnaire"
    # Logic could be more complex if we had more steps, but for now:
    # If empty -> questionnaire
    # If filled -> done (since schedule is "Fixed Weekly Schedule" separate story, check reqs)
    # Story 2.1: "step": "questionnaire" | "schedule" | "done"
    # Let's assume after questionnaire comes schedule.
    
    # Requirement: Return {"is_complete": bool, "step": "questionnaire" | "schedule" | "done"}
    # based on if onboarding_data is empty.
    
    return {
        "is_complete": is_complete,
        "step": step
    }

@router.post("/questionnaire", response_model=Any)
async def submit_questionnaire(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    answers: OnboardingAnswers,
    current_user: Annotated[User, Depends(deps.get_current_user)]
) -> Any:
    """
    Submit Questionnaire (Story 2.2)
    """
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    # Update onboarding_data
    # Helper to convert pydantic to dict, handles enums usually
    profile.onboarding_data = answers.model_dump()
    
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    
    return {"message": "Onboarding questionnaire saved successfully", "step": "schedule"}
