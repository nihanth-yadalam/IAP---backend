<<<<<<< HEAD
"""
Merged User + UserProfile models.

System A provided: email, username, password_hash, profile (JSONB onboarding_data).
System B provided: google_refresh_token.
Merged: google_refresh_token is nullable (not every user links Google).
"""

=======
>>>>>>> main
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base

<<<<<<< HEAD

=======
>>>>>>> main
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
<<<<<<< HEAD
    google_refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # From System B
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    courses: Mapped[list["app.models.task.Course"]] = relationship(
        "Course", back_populates="user", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["app.models.task.Task"]] = relationship(
        "Task", back_populates="user", cascade="all, delete-orphan"
    )
    fixed_slots: Mapped[list["app.models.schedule.FixedSlot"]] = relationship(
        "FixedSlot", back_populates="user", cascade="all, delete-orphan"
    )
    sync_state: Mapped[Optional["app.models.sync.CalendarSyncState"]] = relationship(
        "CalendarSyncState", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

=======
    google_refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
>>>>>>> main

class UserProfile(Base):
    __tablename__ = "user_profiles"

<<<<<<< HEAD
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
=======
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
>>>>>>> main
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    major: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    university: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_archetype: Mapped[str] = mapped_column(String, default="Unclassified")
    onboarding_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    user: Mapped["User"] = relationship("User", back_populates="profile")
