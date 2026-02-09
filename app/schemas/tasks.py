from pydantic import BaseModel, ConfigDict, model_validator, Field
from typing import Optional
from datetime import datetime
from app.models.task import PriorityLevel, TaskCategory, TaskStatus
from app.schemas.courses import CourseInTask

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.Medium
    category: TaskCategory = TaskCategory.Study
    status: TaskStatus = TaskStatus.Pending
    
    # Time Columns
    deadline: Optional[datetime] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    estimated_duration_mins: Optional[int] = None
    
    course_id: Optional[int] = None

class TaskCreate(TaskBase):
    @model_validator(mode='after')
    def check_schedule_times(self):
        if self.scheduled_start_time and not self.scheduled_end_time:
            raise ValueError('scheduled_end_time must be provided if scheduled_start_time is set')
        if self.scheduled_end_time and not self.scheduled_start_time:
            raise ValueError('scheduled_start_time must be provided if scheduled_end_time is set')
        if self.scheduled_start_time and self.scheduled_end_time:
            if self.scheduled_end_time <= self.scheduled_start_time:
                raise ValueError('scheduled_end_time must be after scheduled_start_time')
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

    @model_validator(mode='after')
    def check_schedule_times(self):
        # Only check if both are provided in the update, or if partial update logic is handled elsewhere.
        # For simplicity in Pydantic validation on update, we might need to know the existing state if only one is updated.
        # But here we enforce that IF both are present in the payload, they must be valid.
        if self.scheduled_start_time and self.scheduled_end_time:
             if self.scheduled_end_time <= self.scheduled_start_time:
                raise ValueError('scheduled_end_time must be after scheduled_start_time')
        return self

class TaskResponse(TaskBase):
    id: int
    user_id: int
    created_at: datetime
    course: Optional[CourseInTask] = None
    
    model_config = ConfigDict(from_attributes=True)
