"""
CalendarSyncState model — from System B (unchanged).
Tracks per-user Google Calendar sync token, webhook channel info.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CalendarSyncState(Base):
    __tablename__ = "calendar_sync_state"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    google_calendar_id: Mapped[str] = mapped_column(String, default="primary")

    sync_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    webhook_channel_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    webhook_resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    webhook_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="sync_state")
