from typing import Any, Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.schedule import FixedSlot
from app.schemas.schedule import FixedSlotCreate, FixedSlotResponse

router = APIRouter()

@router.get("/fixed", response_model=List[FixedSlotResponse])
async def get_fixed_schedule(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Get all fixed slots for the current user.
    """
    result = await db.execute(select(FixedSlot).where(FixedSlot.user_id == current_user.id))
    slots = result.scalars().all()
    return slots

@router.post("/fixed", response_model=Any)
async def create_fixed_schedule(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    slots_in: List[FixedSlotCreate],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Manage Fixed Schedule (Story 2.3)
    Bulk insert into fixed_slots.
    """
    # Requirements: "Bulk insert"
    # Should we replace existing or add?
    # "Manage" usually implies setting the state. 
    # For a "Fixed Weekly Schedule" setup, it's often a "set my schedule" action.
    # Let's assume append for now, or maybe clear and set?
    # User Request: "Bulk insert into fixed_slots."
    
    new_slots = []
    for slot_data in slots_in:
        slot = FixedSlot(
            user_id=current_user.id,
            day_of_week=slot_data.day_of_week,
            start_time=slot_data.start_time,
            end_time=slot_data.end_time,
            label=slot_data.label,
            is_google_event=slot_data.is_google_event,
            google_event_id=slot_data.google_event_id
        )
        db.add(slot)
        new_slots.append(slot)
        
    await db.commit()
    
    return {"message": f"Successfully added {len(new_slots)} fixed slots."}
