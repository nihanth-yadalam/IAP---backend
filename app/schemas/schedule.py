"""
Merged Schedule / Slot schemas.

Supports BOTH:
  - System A recurring weekly slots (day_of_week + start_time/end_time + label)
  - System B absolute-datetime slots with Google sync (title + google_start/end_datetime)
"""

from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.schedule import DayOfWeek


# ── System A — recurring weekly slots (onboarding bulk-insert) ───────

class RecurringSlotCreate(BaseModel):
    """Used by POST /schedule/slots (bulk array) for onboarding."""
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    label: str
    is_google_event: bool = False
    google_event_id: Optional[str] = None


# ── System B — absolute datetime slots (Google-synced) ───────────────

class SlotCreate(BaseModel):
    """Used by POST /schedule/slots (single) for calendar events."""
    title: str
    google_start_datetime: datetime
    google_end_datetime: datetime


class SlotUpdate(BaseModel):
    title: Optional[str] = None
    google_start_datetime: Optional[datetime] = None
    google_end_datetime: Optional[datetime] = None


# ── Unified response ─────────────────────────────────────────────────

class SlotResponse(BaseModel):
    id: int
    user_id: int
    title: str
    label: Optional[str] = None

    # Recurring fields
    day_of_week: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    # Google sync fields
    google_start_datetime: Optional[datetime] = None
    google_end_datetime: Optional[datetime] = None
    is_google_event: bool = False
    google_event_id: Optional[str] = None
    last_updated_source: Optional[str] = None
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)
