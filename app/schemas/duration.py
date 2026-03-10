from pydantic import BaseModel, Field
from typing import Literal


class DurationEstimationRequest(BaseModel):
    course_id: int
    task_type: Literal["Assignment", "Exam", "Extracurricular"]
    difficulty: Literal["Easy", "Medium", "Hard"]
    description: str = Field(..., min_length=1, max_length=1000)


class DurationEstimationResponse(BaseModel):
    estimated_duration_mins: int
    reasoning: str
