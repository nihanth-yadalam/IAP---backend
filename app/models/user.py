from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    google_refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    major: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    university: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_archetype: Mapped[str] = mapped_column(String, default="Unclassified")
    onboarding_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    user: Mapped["User"] = relationship("User", back_populates="profile")
