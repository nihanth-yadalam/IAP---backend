"""
Webhook endpoints — from System B, adapted.
M29: POST /webhooks/google-calendar   — receive push notifications from Google
M32: POST /webhooks/setup             — manually set up webhook for current user
"""

from typing import Any, Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.models.user import User
from app.models.sync import CalendarSyncState
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService
from app.services.sync_engine import SyncEngine

router = APIRouter()


def _build_sync_engine() -> SyncEngine:
    oauth = GoogleOAuthService()
    cal = CalendarService(oauth)
    return SyncEngine(oauth, cal)


# ── M29 — Google Calendar webhook receiver ────────────────────────────

@router.post("/google-calendar")
async def google_calendar_webhook(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    x_goog_channel_id: str = Header(None, alias="X-Goog-Channel-ID"),
    x_goog_resource_state: str = Header(None, alias="X-Goog-Resource-State"),
) -> Any:
    """Receive push notifications from Google Calendar."""
    # Confirm webhook handshake
    if x_goog_resource_state == "sync":
        return {"status": "webhook confirmed"}

    if not x_goog_channel_id:
        return {"status": "no channel id"}

    # Parse user_id from channel id: "channel-{user_id}-{uuid}"
    try:
        parts = x_goog_channel_id.split("-")
        if len(parts) >= 2:
            user_id = int(parts[1])
        else:
            return {"status": "invalid channel id format"}
    except (ValueError, IndexError):
        return {"status": "could not parse user_id"}

    engine = _build_sync_engine()
    try:
        await engine.sync_from_google(db, user_id)
        return {"status": "sync completed", "user_id": user_id}
    except Exception as e:
        print(f"Error during webhook sync: {e}")
        return {"status": "sync failed", "error": str(e)}


# ── M32 — Manually set up webhook ────────────────────────────────────

@router.post("/setup")
async def setup_webhook(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Setup webhook channel for the current user."""
    if not current_user.google_refresh_token:
        raise HTTPException(status_code=400, detail="User has not completed Google OAuth")

    if not settings.WEBHOOK_BASE_URL:
        raise HTTPException(status_code=500, detail="WEBHOOK_BASE_URL not configured")

    webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/google-calendar"

    cal = CalendarService(GoogleOAuthService())
    try:
        # Get calendar id from sync state
        result = await db.execute(
            select(CalendarSyncState).where(CalendarSyncState.user_id == current_user.id)
        )
        state = result.scalars().first()
        calendar_id = state.google_calendar_id if state else "primary"

        response = cal.setup_webhook_channel(
            current_user.google_refresh_token, calendar_id, current_user.id, webhook_url
        )

        # Update sync state with webhook info
        if state:
            from datetime import datetime

            state.webhook_channel_id = response.get("id")
            state.webhook_resource_id = response.get("resourceId")
            exp_raw = response.get("expiration")
            if exp_raw:
                try:
                    state.webhook_expires_at = datetime.fromtimestamp(int(exp_raw) / 1000)
                except (ValueError, TypeError):
                    pass
            await db.commit()

        return {
            "status": "webhook configured",
            "channel_id": response.get("id"),
            "webhook_url": webhook_url,
            "expires_at": response.get("expiration"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook setup failed: {e}")
