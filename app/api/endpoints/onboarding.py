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
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Check Onboarding Status
    Story 2.1: Return {"is_complete": bool, "step": "questionnaire" | "schedule" | "done"}
    """
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Step 1: Questionnaire
    if not profile.onboarding_data:
        return {"is_complete": False, "step": "questionnaire"}
    
    # Step 2: Schedule
    # Check if user has any fixed slots
    from app.models.schedule import FixedSlot
    result = await db.execute(select(FixedSlot).where(FixedSlot.user_id == current_user.id))
    slots = result.scalars().first()
    
    if not slots:
        return {"is_complete": False, "step": "schedule"}

    # Step 3: Done
    return {"is_complete": True, "step": "done"}

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
