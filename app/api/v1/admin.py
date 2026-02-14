"""
Admin endpoints — M10: GET /admin/users
JWT-protected, requires admin role.
"""

from typing import Any, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User

router = APIRouter()


@router.get("/users")
async def list_all_users(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    _admin: Annotated[User, Depends(deps.get_current_admin_user)],
) -> Any:
    """List all users (admin only)."""
    result = await db.execute(select(User))
    users = result.scalars().all()

    return {
        "count": len(users),
        "users": [
            {
                "user_id": u.id,
                "email": u.email,
                "username": u.username,
                "google_linked": u.google_refresh_token is not None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }
