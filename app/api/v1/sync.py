"""
Sync management endpoints — from System B, JWT-protected.
M26: POST /sync/trigger            — manual pull from Google
M27: POST /sync/reset/{user_id}    — clear sync token for full resync
M28: GET  /sync/status             — current sync state
M30: POST /sync/push-all           — push un-synced local slots to Google
M31: POST /sync/initialize         — re-initialize calendar sync
"""

from typing import Any, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.models.user import User
from app.models.schedule import FixedSlot
from app.models.sync import CalendarSyncState
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService
from app.services.sync_engine import SyncEngine

router = APIRouter()


def _build_sync_engine() -> SyncEngine:
    oauth = GoogleOAuthService()
    cal = CalendarService(oauth)
    return SyncEngine(oauth, cal)


# ── M26 — Trigger manual sync ────────────────────────────────────────

@router.post("/trigger")
async def trigger_sync(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Manually pull latest events from Google Calendar (incremental sync)."""
    if not current_user.google_refresh_token:
        raise HTTPException(status_code=400, detail="User has not completed Google OAuth")

    engine = _build_sync_engine()
    try:
        await engine.sync_from_google(db, current_user.id)
        return {"status": "sync_completed", "user_id": current_user.id, "synced_at": datetime.utcnow().isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync failed: {exc}")


# ── M27 — Reset sync token ───────────────────────────────────────────

@router.post("/reset")
async def reset_sync(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Clear sync token to force a full resync."""
    result = await db.execute(
        select(CalendarSyncState).where(CalendarSyncState.user_id == current_user.id)
    )
    state = result.scalars().first()
    if state:
        state.sync_token = None
        await db.commit()

    return {
        "status": "sync_token_cleared",
        "user_id": current_user.id,
        "message": "Run POST /api/v1/sync/trigger to perform full resync",
    }


# ── M28 — Sync status ────────────────────────────────────────────────

@router.get("/status")
async def sync_status(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Return current sync state: last sync time, webhook info, etc."""
    result = await db.execute(
        select(CalendarSyncState).where(CalendarSyncState.user_id == current_user.id)
    )
    state = result.scalars().first()

    if not state:
        return {
            "user_id": current_user.id,
            "sync_initialized": False,
            "message": "Calendar sync not initialized. Complete Google OAuth first.",
        }

    return {
        "user_id": current_user.id,
        "sync_initialized": True,
        "google_calendar_id": state.google_calendar_id,
        "has_sync_token": state.sync_token is not None,
        "last_synced_at": state.last_synced_at.isoformat() if state.last_synced_at else None,
        "webhook": {
            "channel_id": state.webhook_channel_id,
            "resource_id": state.webhook_resource_id,
            "expires_at": state.webhook_expires_at.isoformat() if state.webhook_expires_at else None,
            "is_active": (
                state.webhook_expires_at is not None and state.webhook_expires_at > datetime.utcnow()
            ),
        },
    }


# ── M30 — Push all un-synced slots ───────────────────────────────────

@router.post("/push-all")
async def push_all_to_google(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Push all un-synced local slots to Google Calendar."""
    if not current_user.google_refresh_token:
        raise HTTPException(status_code=400, detail="User has not completed Google OAuth")

    engine = _build_sync_engine()

    result = await db.execute(
        select(FixedSlot).where(FixedSlot.user_id == current_user.id, FixedSlot.is_google_event == False)
    )
    slots = result.scalars().all()

    pushed = 0
    errors = []
    for slot in slots:
        try:
            slot.last_updated_source = "APP"
            slot.last_updated_at = datetime.utcnow()
            await db.commit()
            await engine.push_to_google(db, current_user.id, slot.id)
            pushed += 1
        except Exception as exc:
            errors.append({"slot_id": slot.id, "error": str(exc)})

    return {"status": "push_completed", "pushed": pushed, "errors": errors}


# ── M31 — Re-initialize calendar sync ────────────────────────────────

@router.post("/initialize")
async def initialize_calendar_sync(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Re-initialize calendar sync (create state, initial pull, set up webhook)."""
    if not current_user.google_refresh_token:
        raise HTTPException(status_code=400, detail="User has not completed Google OAuth")

    engine = _build_sync_engine()
    webhook_url = None
    if settings.WEBHOOK_BASE_URL:
        webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/google-calendar"

    result = await engine.initialize_sync(db, current_user.id, webhook_url)
    return {"status": "initialized", "user_id": current_user.id, "details": result}
