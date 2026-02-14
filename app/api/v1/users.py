"""
User endpoints — from System A.
M2:  POST /users/              — register
M5:  GET  /users/me            — get current user
M6:  PUT  /users/me/profile    — update profile
M7:  POST /users/me/password   — change password
M8:  POST /users/password-recovery/{email}
M9:  POST /users/reset-password/
"""

from typing import Any, Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security, utils
from app.models.user import User, UserProfile
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserProfileBase,
    UserUpdatePassword,
)

router = APIRouter()


# ── M2 — Register ────────────────────────────────────────────────────

@router.post("/", response_model=UserResponse)
async def create_user(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    user_in: UserCreate,
) -> Any:
    """Create new user."""
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
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create empty profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(user, attribute_names=["profile"])

    return user


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
    print(f"\n[EMAIL SIMULATION] Password Reset Token for {email}:\n{token}\n")
    return {"message": "Password recovery email sent (check terminal)"}


# ── M9 — Reset password ──────────────────────────────────────────────

@router.post("/reset-password/")
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
