"""
Auth endpoints — merged from System A (login) + System B (Google OAuth).
M1: POST /login/access-token  — verify credentials, send OTP
M1b: POST /login/verify-otp   — verify OTP, return JWT
     POST /confirm-email       — confirm email address via token
     POST /resend-confirmation  — resend confirmation email
M3: GET  /google/authorize
M4: GET  /google/callback
"""

from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

import secrets
import urllib.parse

from app.api import deps
from app.core import security, utils
from app.core.config import settings
from app.models.user import User, UserProfile, OTPCode
from app.models.sync import CalendarSyncState
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService
from app.services.sync_engine import SyncEngine
from app.services.email_service import send_otp_email, send_email_confirmation
from app.schemas.user import OTPVerify, EmailConfirmRequest

router = APIRouter()

MAX_OTP_ATTEMPTS = 5
OTP_EXPIRY_MINUTES = 10

# ── Shared service factories ─────────────────────────────────────────

def _oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService()


def _calendar_service() -> CalendarService:
    return CalendarService(_oauth_service())


def _sync_engine() -> SyncEngine:
    oauth = _oauth_service()
    return SyncEngine(oauth, CalendarService(oauth))


# ── M1 — Login (verify credentials → send OTP) ──────────────────────

@router.post("/login/access-token")
async def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(deps.get_db)],
) -> Any:
    """Verify credentials, then send a 6-digit OTP to the user's email."""
    result = await db.execute(
        select(User).where(
            or_(User.email == form_data.username, User.username == form_data.username)
        )
    )
    user = result.scalars().first()

    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if not user.email_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Email not confirmed. Please check your inbox for the confirmation link.",
        )

    # Clean up any existing OTP for this user
    await db.execute(
        delete(OTPCode).where(OTPCode.user_id == user.id, OTPCode.purpose == "login")
    )

    # Generate and store OTP
    code = utils.generate_otp_code()
    otp = OTPCode(
        user_id=user.id,
        email=user.email,
        code=code,
        purpose="login",
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(otp)
    await db.commit()

    # Send OTP email
    send_otp_email(user.email, code)

    return {"status": "otp_pending", "email": user.email}


# ── M1b — Verify OTP ─────────────────────────────────────────────────

@router.post("/login/verify-otp")
async def verify_otp(
    body: OTPVerify,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
) -> Any:
    """Verify the 6-digit OTP and return a JWT access token."""
    result = await db.execute(
        select(OTPCode).where(
            OTPCode.email == body.email,
            OTPCode.purpose == "login",
        )
    )
    otp = result.scalars().first()

    if not otp:
        raise HTTPException(status_code=400, detail="No OTP found. Please log in again.")

    if otp.expires_at < datetime.utcnow():
        await db.delete(otp)
        await db.commit()
        raise HTTPException(status_code=400, detail="OTP expired. Please log in again.")

    if otp.attempts >= MAX_OTP_ATTEMPTS:
        await db.delete(otp)
        await db.commit()
        raise HTTPException(status_code=400, detail="Too many attempts. Please log in again.")

    if otp.code != body.otp:
        otp.attempts += 1
        await db.commit()
        remaining = MAX_OTP_ATTEMPTS - otp.attempts
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
        )

    # OTP is valid — issue JWT
    user_id = otp.user_id
    await db.delete(otp)
    await db.commit()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(user_id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }


# ── Email confirmation ────────────────────────────────────────────────

@router.post("/confirm-email")
async def confirm_email(
    body: EmailConfirmRequest,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
) -> Any:
    """Confirm a user's email address using the token sent during registration."""
    email = utils.verify_email_confirmation_token(body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation link.")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.email_confirmed:
        return {"message": "Email already confirmed."}

    user.email_confirmed = True
    await db.commit()
    return {"message": "Email confirmed successfully. You can now sign in."}


@router.post("/resend-confirmation")
async def resend_confirmation(
    email: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Resend the email confirmation link."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        # Don't reveal whether the email exists
        return {"message": "If that email is registered, a new confirmation link has been sent."}

    if user.email_confirmed:
        return {"message": "Email is already confirmed."}

    token = utils.generate_email_confirmation_token(user.email)
    send_email_confirmation(user.email, token)
    return {"message": "If that email is registered, a new confirmation link has been sent."}


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
            email_confirmed=True,  # Google has already verified the email
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
