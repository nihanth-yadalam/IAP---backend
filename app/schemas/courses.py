from pydantic import BaseModel, ConfigDict
from typing import Optional


class CourseBase(BaseModel):
    name: str
    code: Optional[str] = None
    color_code: str
    term: Optional[str] = None
    is_archived: bool = False


class CourseCreate(CourseBase):
    pass


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
