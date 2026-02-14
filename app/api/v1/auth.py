"""
Auth endpoints — merged from System A (login) + System B (Google OAuth).
M1: POST /login/access-token
M3: GET  /google/authorize
M4: GET  /google/callback
"""

from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.models.sync import CalendarSyncState
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService
from app.services.sync_engine import SyncEngine

router = APIRouter()

# ── Shared service factories ─────────────────────────────────────────

def _oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService()


def _calendar_service() -> CalendarService:
    return CalendarService(_oauth_service())


def _sync_engine() -> SyncEngine:
    oauth = _oauth_service()
    return SyncEngine(oauth, CalendarService(oauth))


# ── M1 — Login ───────────────────────────────────────────────────────

@router.post("/login/access-token")
async def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(deps.get_db)],
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    result = await db.execute(
        select(User).where(
            or_(User.email == form_data.username, User.username == form_data.username)
        )
    )
    user = result.scalars().first()

    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }


# ── M3 — Google authorize ────────────────────────────────────────────

@router.get("/google/authorize")
async def google_authorize(
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Get Google OAuth authorization URL.
    JWT required — state embeds user id for callback verification.
    """
    oauth = _oauth_service()
    state = f"{current_user.id}"
    auth_url = oauth.get_authorization_url(state=state)
    return {
        "authorization_url": auth_url,
        "instructions": "Open this URL in your browser to authorize with Google",
    }


# ── M4 — Google callback ─────────────────────────────────────────────

@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
) -> Any:
    """
    Handle OAuth callback, store refresh token, auto-initialize calendar sync.
    The `state` parameter carries the user_id set during /google/authorize.
    """
    try:
        user_id = int(state)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    oauth = _oauth_service()
    try:
        tokens = oauth.exchange_code_for_tokens(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {e}")

    # Save refresh token on the user
    user.google_refresh_token = tokens["refresh_token"]
    await db.commit()

    # Auto-initialize calendar sync
    engine = _sync_engine()
    webhook_url = None
    if settings.WEBHOOK_BASE_URL:
        webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/google-calendar"

    sync_status = await engine.initialize_sync(db, user_id, webhook_url)

    return {
        "status": "success",
        "message": "Authorization successful! Calendar sync initialized.",
        "user_id": user.id,
        "email": user.email,
        "sync": sync_status,
    }
