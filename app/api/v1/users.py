"""
User endpoints — from System A.
M2:  POST /users/              — register
M5:  GET  /users/me            — get current user
M6:  PUT  /users/me/profile    — update profile
M7:  POST /users/me/password   — change password
M8:  POST /users/password-recovery/{email}
M9:  POST /users/reset-password/
M22: GET  /users/me/memory
M23: GET  /users/me/memory/summaries
M24: POST /users/me/memory/rules
M25: POST /users/me/reflexion/trigger
"""

from typing import Any, Annotated, List

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security, utils
from app.models.user import User, UserProfile
from app.models.task import ReflexionLog
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserProfileBase,
    UserUpdatePassword,
    GlobalMemorySettingsUpdate,
)
from app.services.email_service import send_email_confirmation

router = APIRouter()


# ── M2 — Register ────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_user(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    user_in: UserCreate,
) -> Any:
    """Create new user and send email confirmation."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system.")

    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="The user with this username already exists in the system.")

    user = User(
        email=user_in.email,
        username=user_in.username,
        password_hash=security.get_password_hash(user_in.password),
        email_confirmed=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create empty profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(user, attribute_names=["profile"])

    # Send confirmation email
    token = utils.generate_email_confirmation_token(user.email)
    email_sent = send_email_confirmation(user.email, token)

    return {
        "message": "Account created. Please check your email to confirm your address.",
        "email": user.email,
        "email_sent": email_sent,
    }


# ── M5 — Get current user ────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: Annotated[User, Depends(deps.get_current_user)],
    db: Annotated[AsyncSession, Depends(deps.get_db)],
) -> Any:
    """Get current user."""
    return current_user


# ── M6 — Update profile ──────────────────────────────────────────────

@router.put("/me/profile", response_model=UserResponse)
async def update_user_profile(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    profile_in: UserProfileBase,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Update own profile."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in profile_in.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return current_user


# ── Set timezone (lightweight, called silently from frontend) ────────

@router.put("/me/timezone")
async def set_timezone(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    tz: str = Body(..., embed=True),
) -> Any:
    """Set the user's timezone (e.g. 'Asia/Kolkata')."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    profile.timezone = tz
    await db.commit()
    return {"timezone": tz}


# ── M7 — Change password ─────────────────────────────────────────────

@router.post("/me/password")
async def update_password(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    password_in: UserUpdatePassword,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Update own password."""
    if not security.verify_password(password_in.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password")

    if password_in.current_password == password_in.new_password:
        raise HTTPException(status_code=400, detail="New password cannot be the same as the current password")

    current_user.password_hash = security.get_password_hash(password_in.new_password)
    db.add(current_user)
    await db.commit()
    return {"message": "Password updated successfully"}


# ── M8 — Password recovery ───────────────────────────────────────────

@router.post("/password-recovery/{email}")
async def recover_password(
    email: str,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
) -> Any:
    """Password Recovery — generate reset token (email simulated)."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="The user with this email does not exist in the system.")

    token = utils.generate_password_reset_token(email=email)

    # Send real email
    from app.services.email_service import send_password_reset_email
    email_sent = send_password_reset_email(to_email=email, token=token)

    if email_sent:
        return {"message": "Password recovery email sent. Check your inbox."}
    else:
        # Fallback: return token in response (dev mode only)
        return {
            "message": "SMTP not configured. Use the token below to reset password.",
            "token": token,
        }

# ── M9 — Reset password ──────────────────────────────────────────────

@router.post("/reset-password")
async def reset_password(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    token: str = Body(...),
    new_password: str = Body(...),
) -> Any:
    """Reset password using token."""
    email = utils.verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="The user for this token does not exist in the system.")

    user.password_hash = security.get_password_hash(new_password)
    db.add(user)
    await db.commit()
    return {"message": "Password updated successfully"}


# ── M22 — Get AI memory ──────────────────────────────────────────────

@router.get("/me/memory")
async def get_user_memory(
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Returns the full memory JSONB for the authenticated user."""
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.onboarding_data or {}


# ── M23 — Get recent reflexion summaries ─────────────────────────────

@router.get("/me/memory/summaries")
async def get_memory_summaries(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Returns the 5 most recent reflexion log rows for insights section."""
    result = await db.execute(
        select(ReflexionLog)
        .where(ReflexionLog.user_id == current_user.id)
        .order_by(ReflexionLog.generated_at.desc())
        .limit(5)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "generated_at": log.generated_at.isoformat(),
            "summary_text": log.summary_text,
            "updated_traits": log.updated_traits,
            "reflexion_trigger": log.reflexion_trigger,
        }
        for log in logs
    ]


# ── M24 — Add manual rule to generic memory ─────────────────────────

@router.post("/me/memory/rules")
async def add_memory_rule(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    rule: str = Body(..., embed=True),
) -> Any:
    """Appends a text rule to manual_rules in generic memory."""
    import json

    await db.execute(
        text(
            """
            UPDATE user_profiles
            SET onboarding_data = jsonb_set(
                COALESCE(onboarding_data, '{}'::jsonb),
                '{manual_rules}',
                COALESCE(onboarding_data->'manual_rules', '[]'::jsonb) || :rule_json::jsonb,
                true
            )
            WHERE user_id = :user_id
            """
        ),
        {"user_id": current_user.id, "rule_json": json.dumps(rule)},
    )
    await db.commit()
    return {"message": "Rule added successfully", "rule": rule}


@router.put("/me/memory/rules/{index}")
async def update_memory_rule(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    index: int,
    current_user: Annotated[User, Depends(deps.get_current_user)],
    rule: str = Body(..., embed=True),
) -> Any:
    """Updates a text rule at a specific index in manual_rules."""
    import json
    from sqlalchemy import text

    # We use jsonb_set with a path array constructed directly in SQL
    # using the element index. Note: Postgres jsonb arrays are 0-indexed.
    await db.execute(
        text(
            """
            UPDATE user_profiles
            SET onboarding_data = jsonb_set(
                onboarding_data,
                ARRAY['manual_rules', :index_str],
                :rule_json::jsonb,
                false
            )
            WHERE user_id = :user_id 
              AND jsonb_array_length(onboarding_data->'manual_rules') > :index
            """
        ),
        {
            "user_id": current_user.id, 
            "index_str": str(index), 
            "index": index,
            "rule_json": json.dumps(rule)
        },
    )
    await db.commit()
    return {"message": "Rule updated successfully", "index": index, "rule": rule}


@router.delete("/me/memory/rules/{index}")
async def delete_memory_rule(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    index: int,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Deletes a text rule at a specific index in manual_rules."""
    from sqlalchemy import text

    # The minus operator removes an element from a jsonb array by index
    await db.execute(
        text(
            """
            UPDATE user_profiles
            SET onboarding_data = onboarding_data #- ARRAY['manual_rules', :index_str]
            WHERE user_id = :user_id
              AND jsonb_array_length(onboarding_data->'manual_rules') > :index
            """
        ),
        {
            "user_id": current_user.id, 
            "index_str": str(index), 
            "index": index
        },
    )
    await db.commit()
    return {"message": "Rule deleted successfully", "index": index}


# ── M25 — Update memory settings (global) ───────────────────────────

@router.put("/me/memory/settings")
async def update_memory_settings(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    settings: GlobalMemorySettingsUpdate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Update global AI memory settings (chronotype, base energy, etc)."""
    import json
    from sqlalchemy import text

    updates = settings.model_dump(exclude_unset=True)
    if not updates:
        return {"message": "No settings to update"}

    # Dynamically build the jsonb_set string because the key is dynamic
    # Or just execute one by one
    for key, val in updates.items():
        await db.execute(
            text(
                f"""
                UPDATE user_profiles
                SET onboarding_data = jsonb_set(
                    COALESCE(onboarding_data, '{{}}'::jsonb),
                    '{{global_settings, {key}}}',
                    :val_json::jsonb,
                    true
                )
                WHERE user_id = :user_id
                """
            ),
            {"user_id": current_user.id, "val_json": json.dumps(val)}
        )
    await db.commit()
    return {"message": "Memory settings updated successfully"}


# ── M26 — Manually trigger reflexion ─────────────────────────────────

@router.post("/me/reflexion/trigger")
async def trigger_reflexion(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    background_tasks: BackgroundTasks,
) -> Any:
    """Manually trigger reflexion agent for the current user."""
    from app.services.reflexion_agent import run_reflexion_agent

    background_tasks.add_task(run_reflexion_agent, current_user.id, db, "manual")
    return {"message": "Reflexion triggered. Results will be available shortly."}
