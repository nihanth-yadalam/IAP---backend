"""
Schedule endpoints — MERGED from System A (recurring slots) + System B (calendar slots with Google sync).

M21: GET    /schedule/fixed            — list all slots (recurring + calendar)
M22: POST   /schedule/fixed            — bulk-create recurring slots (System A)
M23: POST   /schedule/slots            — create a calendar slot + push to Google (System B)
M24: PUT    /schedule/slots/{slot_id}  — update a slot + push to Google
M25: DELETE /schedule/slots/{slot_id}  — soft-delete a slot + push to Google
"""

from typing import Any, Annotated, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.schedule import FixedSlot
from app.schemas.schedule import RecurringSlotCreate, SlotCreate, SlotUpdate, SlotResponse
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService
from app.services.sync_engine import SyncEngine

router = APIRouter()


# ── Service factories ─────────────────────────────────────────────────

def _build_sync_engine() -> SyncEngine:
    oauth = GoogleOAuthService()
    cal = CalendarService(oauth)
    return SyncEngine(oauth, cal)


# ── M21 — List all fixed / calendar slots ─────────────────────────────

@router.get("/fixed", response_model=List[SlotResponse])
async def get_fixed_schedule(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Get all fixed / calendar slots for the current user."""
    result = await db.execute(
        select(FixedSlot).where(FixedSlot.user_id == current_user.id, FixedSlot.is_deleted == False)
    )
    return result.scalars().all()


# ── M22 — Bulk-create recurring slots (System A pattern) ─────────────

@router.post("/fixed")
async def create_fixed_schedule(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    slots_in: List[RecurringSlotCreate],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Bulk insert recurring fixed slots (onboarding step)."""
    new_slots = []
    for slot_data in slots_in:
        slot = FixedSlot(
            user_id=current_user.id,
            day_of_week=slot_data.day_of_week,
            start_time=slot_data.start_time,
            end_time=slot_data.end_time,
            label=slot_data.label,
            title=slot_data.label,  # use label as title for unified display
            is_google_event=False,
        )
        db.add(slot)
        new_slots.append(slot)

    await db.commit()
    return {"message": f"Successfully added {len(new_slots)} fixed slots."}


# ── M23 — Create a calendar slot + push to Google ────────────────────

@router.post("/slots", response_model=SlotResponse)
async def create_slot(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    slot_data: SlotCreate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Create a calendar slot and push to Google Calendar."""
    slot = FixedSlot(
        user_id=current_user.id,
        title=slot_data.title,
        google_start_datetime=slot_data.google_start_datetime,
        google_end_datetime=slot_data.google_end_datetime,
        last_updated_source="APP",
        last_updated_at=datetime.utcnow(),
        is_google_event=False,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)

    # Push to Google if user has linked account
    if current_user.google_refresh_token:
        engine = _build_sync_engine()
        try:
            await engine.push_to_google(db, current_user.id, slot.id)
            await db.refresh(slot)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to sync to Google: {e}")

    return slot


# ── M24 — Update a slot + push ───────────────────────────────────────

@router.put("/slots/{slot_id}", response_model=SlotResponse)
async def update_slot(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    slot_id: int,
    slot_data: SlotUpdate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Update a slot and push changes to Google Calendar."""
    result = await db.execute(
        select(FixedSlot).where(FixedSlot.id == slot_id, FixedSlot.user_id == current_user.id)
    )
    slot = result.scalars().first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    update_fields = slot_data.model_dump(exclude_unset=True)
    update_fields["last_updated_source"] = "APP"
    update_fields["last_updated_at"] = datetime.utcnow()

    for field, value in update_fields.items():
        setattr(slot, field, value)

    await db.commit()
    await db.refresh(slot)

    # Push to Google
    if current_user.google_refresh_token and slot.is_google_event:
        engine = _build_sync_engine()
        try:
            await engine.push_to_google(db, current_user.id, slot.id)
            await db.refresh(slot)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to sync to Google: {e}")

    return slot


# ── M25 — Soft-delete a slot + push ──────────────────────────────────

@router.delete("/slots/{slot_id}")
async def delete_slot(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    slot_id: int,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Soft-delete a slot and sync deletion to Google Calendar."""
    result = await db.execute(
        select(FixedSlot).where(FixedSlot.id == slot_id, FixedSlot.user_id == current_user.id)
    )
    slot = result.scalars().first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot.is_deleted = True
    slot.last_updated_source = "APP"
    slot.last_updated_at = datetime.utcnow()
    await db.commit()

    # Push deletion to Google
    if current_user.google_refresh_token and slot.is_google_event and slot.google_event_id:
        engine = _build_sync_engine()
        try:
            await engine.push_to_google(db, current_user.id, slot.id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to sync to Google: {e}")

    return {"status": "deleted", "slot_id": slot_id}
