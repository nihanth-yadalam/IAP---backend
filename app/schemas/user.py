from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str

class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    major: Optional[str] = None
    university: Optional[str] = None
    current_archetype: Optional[str] = "Unclassified"
    onboarding_data: Optional[dict[str, Any]] = {}

class UserResponse(UserBase):
    id: int
    profile: Optional[UserProfileBase] = None
    
    model_config = ConfigDict(from_attributes=True)
