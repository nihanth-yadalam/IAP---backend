from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class CourseMemoryUpdate(BaseModel):
    confidence_score: Optional[int] = Field(None, ge=1, le=10)
    drain_rate: Optional[int] = Field(None, ge=1, le=10)


class CourseBase(BaseModel):
    name: str
    code: Optional[str] = None
    color_code: str
    term: Optional[str] = None
    is_archived: bool = False


class CourseCreate(CourseBase):
    confidence_score: int = Field(default=5, ge=1, le=10, description="Self-assessed confidence 1-10")
    drain_rate: int = Field(default=5, ge=1, le=10, description="Perceived mental drain 1-10")


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    color_code: Optional[str] = None
    term: Optional[str] = None
    is_archived: Optional[bool] = None


class CourseInTask(BaseModel):
    id: int
    name: str
    color_code: str
    model_config = ConfigDict(from_attributes=True)


class CourseResponse(CourseBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
