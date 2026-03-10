"""
Auth endpoints — merged from System A (login) + System B (Google OAuth).
M1: POST /login/access-token
M3: GET  /google/authorize
M4: GET  /google/callback
"""

from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import secrets
import urllib.parse

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User, UserProfile
from app.models.sync import CalendarSyncState
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService
from app.services.sync_engine import SyncEngine
from app.services.email_service import send_login_confirmation_email, send_otp_email

router = APIRouter()

# ── OTP store: {email: {"otp": str, "username": str, "expires_at": datetime}} ──
import datetime as _dt
_otp_store: dict[str, dict] = {}

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

    # Generate a 6-digit OTP, store with 10-minute expiry, send via email
    otp = f"{secrets.randbelow(1000000):06d}"
    _otp_store[user.email] = {
        "otp": otp,
        "username": user.username,
        "user_id": user.id,
        "expires_at": _dt.datetime.utcnow() + _dt.timedelta(minutes=10),
    }
    send_otp_email(user.email, user.username, otp)

    return {"status": "otp_pending", "email": user.email}


@router.post("/login/verify-otp")
async def verify_login_otp(
    payload: dict,
) -> Any:
    """Verify the OTP sent to the user's email and return a JWT on success."""
    email: str = payload.get("email", "").strip().lower()
    otp: str = str(payload.get("otp", "")).strip()

    entry = _otp_store.get(email)
    if not entry:
        raise HTTPException(status_code=400, detail="No pending OTP for this email. Please log in again.")

    if _dt.datetime.utcnow() > entry["expires_at"]:
        _otp_store.pop(email, None)
        raise HTTPException(status_code=400, detail="OTP has expired. Please log in again.")

    if not secrets.compare_digest(entry["otp"], otp):
        raise HTTPException(status_code=400, detail="Incorrect OTP.")

    _otp_store.pop(email, None)  # single-use

    # Send login confirmation notification now that login is complete
    send_login_confirmation_email(email, entry["username"])

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(entry["user_id"], expires_delta=access_token_expires),
        "token_type": "bearer",
    }


# ── Google Sign-In (no JWT required) ────────────────────────────────

@router.get("/google/login/debug")
async def google_login_debug() -> dict:
    """Return the OAuth URL without redirecting — use this to confirm the redirect_uri."""
    oauth = _oauth_service()
    auth_url = oauth.get_login_authorization_url(state="google_login")
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)
    return {
        "redirect_uri_sent_to_google": params.get("redirect_uri", [None])[0],
        "full_authorization_url": auth_url,
    }


@router.get("/google/login")
async def google_login_start() -> RedirectResponse:
    """Redirect the browser directly to Google's sign-in consent screen."""
    oauth = _oauth_service()
    auth_url = oauth.get_login_authorization_url(state="google_login")
    return RedirectResponse(url=auth_url)


@router.get("/google/login/callback")
async def google_login_callback(
    code: str,
    state: str,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
) -> RedirectResponse:
    """
    Handle Google Sign-In callback.
    Creates a new account if the email is not yet registered, then issues a JWT
    and redirects the browser to the frontend with the token as a query param.
    """
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    oauth = _oauth_service()

    try:
        user_info = oauth.exchange_login_code_for_user_info(code)
    except Exception as exc:
        msg = urllib.parse.quote(str(exc))
        return RedirectResponse(
            url=f"{frontend_url}/auth/google/callback?status=error&message={msg}"
        )

    email = user_info.get("email")
    name = user_info.get("name", "")

    if not email:
        return RedirectResponse(
            url=f"{frontend_url}/auth/google/callback?status=error&message=No+email+returned+from+Google"
        )

    # Find or create the user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        # Derive a unique username from the email local-part
        base = email.split("@")[0]
        username, suffix = base, 1
        while True:
            taken = await db.execute(select(User).where(User.username == username))
            if not taken.scalars().first():
                break
            username = f"{base}{suffix}"
            suffix += 1

        user = User(
            email=email,
            username=username,
            # Google-authenticated users have no usable password
            password_hash=security.get_password_hash(secrets.token_urlsafe(32)),
        )
        db.add(user)
        await db.flush()  # populate user.id

        profile = UserProfile(user_id=user.id, full_name=name)
        db.add(profile)
        await db.commit()
        await db.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)

    return RedirectResponse(
        url=f"{frontend_url}/auth/google/callback?status=success&token={urllib.parse.quote(token)}"
    )


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
) -> RedirectResponse:
    """
    Handle OAuth callback, store refresh token, auto-initialize calendar sync.
    Redirects to the frontend with status query params.
    """
    frontend_url = settings.FRONTEND_URL.rstrip("/")

    try:
        user_id = int(state)
    except (ValueError, TypeError):
        return RedirectResponse(
            url=f"{frontend_url}/oauth/callback?status=error&message=Invalid+OAuth+state"
        )

    user = await db.get(User, user_id)
    if not user:
        return RedirectResponse(
            url=f"{frontend_url}/oauth/callback?status=error&message=User+not+found"
        )

    oauth = _oauth_service()
    try:
        tokens = oauth.exchange_code_for_tokens(code)
    except Exception as e:
        msg = urllib.parse.quote(str(e))
        return RedirectResponse(
            url=f"{frontend_url}/oauth/callback?status=error&message={msg}"
        )

    # Save refresh token on the user
    user.google_refresh_token = tokens["refresh_token"]
    await db.commit()

    # Auto-initialize calendar sync
    engine = _sync_engine()
    webhook_url = None
    if settings.WEBHOOK_BASE_URL:
        webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/google-calendar"

    try:
        await engine.initialize_sync(db, user_id, webhook_url)
    except Exception:
        pass  # Non-critical — sync can be triggered manually later

    return RedirectResponse(
        url=f"{frontend_url}/oauth/callback?status=success"
    )
