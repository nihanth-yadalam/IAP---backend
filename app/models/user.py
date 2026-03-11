"""
Merged User + UserProfile models.

System A provided: email, username, password_hash, profile (JSONB onboarding_data).
System B provided: google_refresh_token.
Merged: google_refresh_token is nullable (not every user links Google).
"""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    google_refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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
    task_logs: Mapped[list["app.models.task.TaskLog"]] = relationship(
        "TaskLog", back_populates="user", cascade="all, delete-orphan"
    )
    reflexion_logs: Mapped[list["app.models.task.ReflexionLog"]] = relationship(
        "ReflexionLog", back_populates="user", cascade="all, delete-orphan"
    )
    fixed_slots: Mapped[list["app.models.schedule.FixedSlot"]] = relationship(
        "FixedSlot", back_populates="user", cascade="all, delete-orphan"
    )
    sync_state: Mapped[Optional["app.models.sync.CalendarSyncState"]] = relationship(
        "CalendarSyncState", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    major: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    university: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="UTC")
    current_archetype: Mapped[str] = mapped_column(String, default="Unclassified")
    onboarding_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_reflexion_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    persona_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped["User"] = relationship("User", back_populates="profile")


class OTPCode(Base):
    """Stores one-time passcodes for login verification and email confirmation."""
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False, default="login")  # "login" | "email_confirmation"
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
