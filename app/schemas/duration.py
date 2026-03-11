from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date, time


class DurationEstimationRequest(BaseModel):
    course_id: int
    task_type: Literal["Assignment", "Exam", "Extracurricular"]
    difficulty: Literal["Easy", "Medium", "Hard"]
    description: str = Field(..., min_length=1, max_length=1000)


class DurationEstimationResponse(BaseModel):
    estimated_duration_mins: int
    reasoning: str


# ── Scheduling Schemas ───────────────────────────────────────────────


class SlotRecommendationRequest(BaseModel):
    course_id: int
    task_type: Literal["Assignment", "Exam", "Extracurricular"]
    difficulty: Literal["Easy", "Medium", "Hard"]
    description: str
    estimated_duration_mins: int = Field(..., ge=15, le=480)
    period_start: date
    period_end: date


class RecommendedSlot(BaseModel):
    rank: int
    day: str
    date: date
    start_time: time
    end_time: time
    time_block: str
    reasoning: str


class SlotRecommendationResponse(BaseModel):
    recommendations: list[RecommendedSlot]
    scheduling_note: Optional[str] = None


class ConfirmSlotRequest(BaseModel):
    task_id: int
    scheduled_date: date
    scheduled_start_time: time
    scheduled_end_time: time

