from typing import AsyncGenerator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core import security
from app.db.session import SessionLocal
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

async def get_current_user(
    token: Annotated[str, Depends(reusable_oauth2)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = payload.get("sub")
        if token_data is None:
            raise credentials_exception
    except (JWTError, ValidationError):
        raise credentials_exception
    
    # Check if the token subject is an ID (int) or email (str)
    # The create_access_token uses str(subject), so it's a string in the token.
    # Depending on what we put in 'sub' (id or email), we query accordingly.
    # Let's assume we put the User ID in 'sub'.
    
    try:
        user_id = int(token_data)
    except ValueError:
         raise credentials_exception

    result = await db.execute(select(User).options(selectinload(User.profile)).where(User.id == user_id))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    return user
