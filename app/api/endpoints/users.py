from typing import Any, Annotated
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core import security
from app.models.user import User, UserProfile
from app.schemas.user import UserCreate, UserResponse, UserProfileBase, UserLogin

router = APIRouter()
# email is being considered as username. needs a fix.
@router.post("/", response_model=UserResponse)
async def create_user(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    user_in: UserCreate
) -> Any:
    """
    Create new user.
    """
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Check username uniqueness
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
        
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
    # Refresh user to load profile relation
    await db.refresh(user, attribute_names=["profile"])
    
    return user

@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: Annotated[User, Depends(deps.get_current_user)],
    db: Annotated[AsyncSession, Depends(deps.get_db)] # to ensure lazy loads if needed
) -> Any:
    """
    Get current user.
    """
    # Force load profile if not loaded (though we specifically designed it to be available)
    # The relationship is lazy='select' by default or similar.
    # In async, we need to be careful with lazy loading.
    # We might need to select options(joinedload(User.profile)) in deps.get_current_user
    # or rely on explicit refresh/loading.
    
    # Simple fix: in deps.get_current_user, we can use joinedload.
    # For now, let's see if it works or if we need to update deps.py.
    # Actually, let's update this endpoint to ensure we have the profile.
    
    # If using Pydantic from_attributes=True, it tries to access attributes.
    # If attribute is not loaded in async session, it might fail with Greenlet error unless specific config.
    # We'll rely on the fact that we might need to eager load it.
    
    # We will fix deps.py in the next step to use 'select(User).options(joinedload(User.profile))'.
    return current_user

@router.put("/me/profile", response_model=UserResponse)
async def update_user_profile(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    profile_in: UserProfileBase,
    current_user: Annotated[User, Depends(deps.get_current_user)]
) -> Any:
    """
    Update own profile.
    """
    # Assuming profile exists because we create it on signup
    # We need to fetch profile or access via relationship
    
    # Re-fetch with profile to be safe and writable
    # (current_user from deps might be detached or simple select)
    
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    
    if not profile:
        # Should not happen per our logic, but handle it
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    
    # Return user with updated profile
    # We need to refresh the user's profile relationship?
    # Or just return the user object which usually works if session is alive.
    return current_user
