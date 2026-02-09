from datetime import time
from typing import Optional, List
from pydantic import BaseModel
from app.models.schedule import DayOfWeek

class FixedSlotBase(BaseModel):
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    label: str
    is_google_event: bool = False
    google_event_id: Optional[str] = None

class FixedSlotCreate(FixedSlotBase):
    pass

class FixedSlotResponse(FixedSlotBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
