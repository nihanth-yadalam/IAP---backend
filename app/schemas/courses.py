from pydantic import BaseModel, ConfigDict
from typing import Optional

<<<<<<< HEAD

=======
>>>>>>> main
class CourseBase(BaseModel):
    name: str
    color_code: str
    is_archived: bool = False

<<<<<<< HEAD

class CourseCreate(CourseBase):
    pass


=======
class CourseCreate(CourseBase):
    pass

>>>>>>> main
class CourseUpdate(BaseModel):
    name: Optional[str] = None
    color_code: Optional[str] = None
    is_archived: Optional[bool] = None

<<<<<<< HEAD

=======
>>>>>>> main
class CourseInTask(BaseModel):
    id: int
    name: str
    color_code: str
    model_config = ConfigDict(from_attributes=True)

<<<<<<< HEAD

class CourseResponse(CourseBase):
    id: int
    user_id: int

=======
class CourseResponse(CourseBase):
    id: int
    user_id: int
    
>>>>>>> main
    model_config = ConfigDict(from_attributes=True)
