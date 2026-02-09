from sqlalchemy import Column, Integer, String, Time, Boolean, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum

class DayOfWeek(str, enum.Enum):
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"
    Saturday = "Saturday"
    Sunday = "Sunday"

class FixedSlot(Base):
    __tablename__ = "fixed_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    day_of_week: Mapped[DayOfWeek] = mapped_column(String, nullable=False) # store as string in DB
    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    
    is_google_event: Mapped[bool] = mapped_column(Boolean, default=False)
    google_event_id: Mapped[str | None] = mapped_column(String, nullable=True) # CRITICAL for Epic 2 compatibility

    user = relationship("User", backref="fixed_slots")
