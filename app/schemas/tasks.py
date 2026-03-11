from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, Any
from datetime import datetime
from app.models.task import PriorityLevel, TaskCategory, TaskStatus
from app.schemas.courses import CourseInTask


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.Medium
    category: TaskCategory = TaskCategory.Study
    status: TaskStatus = TaskStatus.Pending

    deadline: Optional[datetime] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    estimated_duration_mins: Optional[int] = None

    course_id: Optional[int] = None


class TaskCreate(TaskBase):
    @model_validator(mode="after")
    def check_schedule_times(self):
        if self.scheduled_start_time and not self.scheduled_end_time:
            raise ValueError(
                "scheduled_end_time must be provided if scheduled_start_time is set"
            )
        if self.scheduled_end_time and not self.scheduled_start_time:
            raise ValueError(
                "scheduled_start_time must be provided if scheduled_end_time is set"
            )
        if self.scheduled_start_time and self.scheduled_end_time:
            if self.scheduled_end_time <= self.scheduled_start_time:
                raise ValueError(
                    "scheduled_end_time must be after scheduled_start_time"
                )
        return self


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PriorityLevel] = None
    category: Optional[TaskCategory] = None
    status: Optional[TaskStatus] = None
    deadline: Optional[datetime] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    estimated_duration_mins: Optional[int] = None
    course_id: Optional[int] = None
    parent_task_id: Optional[int] = None

    @model_validator(mode="after")
    def check_schedule_times(self):
        if self.scheduled_start_time and self.scheduled_end_time:
            if self.scheduled_end_time <= self.scheduled_start_time:
                raise ValueError(
                    "scheduled_end_time must be after scheduled_start_time"
                )
        return self


class TaskResponse(TaskBase):
    id: int
    user_id: int
    created_at: datetime
    google_event_id: Optional[str] = None
    course: Optional[CourseInTask] = None

    model_config = ConfigDict(from_attributes=True)


# ── Task Feedback / Completion ───────────────────────────────────────


class TaskFeedbackRequest(BaseModel):
    actual_duration_mins: int = Field(..., gt=0, description="How long the task actually took (minutes)")
    drain_intensity: int = Field(..., ge=1, le=10, description="Mental drain 1-10")
    mood_note: Optional[str] = None


class TaskLogResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    actual_duration_mins: int
    drain_intensity: int
    mood_note: Optional[str] = None
    completion_time: datetime
    time_block: str
    was_on_time: bool
    delay_mins: int
    duration_ratio: float
    ai_feedback_tags: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
