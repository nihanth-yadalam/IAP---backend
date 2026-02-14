<<<<<<< HEAD
"""
Merged FixedSlot model.

System A provided: day_of_week / start_time / end_time / label (recurring weekly blocks).
System B provided: google_start_datetime / google_end_datetime / title + full Google sync fields.
Merged: keeps BOTH representations.  Recurring fields are used for onboarding/collision checks;
        datetime fields are used for Google Calendar synchronization.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, String, Boolean, ForeignKey, DateTime, Time, CheckConstraint,
)
=======
from sqlalchemy import Column, Integer, String, Time, Boolean, ForeignKey, Enum
>>>>>>> main
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum

<<<<<<< HEAD

=======
>>>>>>> main
class DayOfWeek(str, enum.Enum):
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"
    Saturday = "Saturday"
    Sunday = "Sunday"

<<<<<<< HEAD

=======
>>>>>>> main
class FixedSlot(Base):
    __tablename__ = "fixed_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
<<<<<<< HEAD
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # ── Display / identity ───────────────────────────────────────────
    title: Mapped[str] = mapped_column(String, nullable=False)         # System B name
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # System A alias

    # ── Absolute datetimes (System B — Google Calendar sync) ─────────
    google_start_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    google_end_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Recurring weekly fields (System A — onboarding / collision) ──
    day_of_week: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    start_time = mapped_column(Time, nullable=True)
    end_time = mapped_column(Time, nullable=True)

    # ── Google sync metadata (System B) ──────────────────────────────
    is_google_event: Mapped[bool] = mapped_column(Boolean, default=False)
    google_event_id: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    last_updated_source: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Relationships ────────────────────────────────────────────────
    user = relationship("User", back_populates="fixed_slots")

    __table_args__ = (
        CheckConstraint("last_updated_source IN ('APP', 'GOOGLE')", name="ck_updated_source"),
    )
=======
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    day_of_week: Mapped[DayOfWeek] = mapped_column(String, nullable=False) # store as string in DB
    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    
    is_google_event: Mapped[bool] = mapped_column(Boolean, default=False)
    google_event_id: Mapped[str | None] = mapped_column(String, nullable=True) # CRITICAL for Epic 2 compatibility

    user = relationship("User", backref="fixed_slots")
>>>>>>> main
