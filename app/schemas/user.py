from pydantic import BaseModel, EmailStr, ConfigDict, model_validator
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


class PasswordReset(BaseModel):
    token: str
    new_password: str
    email: EmailStr


class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    major: Optional[str] = None
    university: Optional[str] = None
    timezone: Optional[str] = "UTC"
    current_archetype: Optional[str] = "Unclassified"
    onboarding_data: Optional[dict[str, Any]] = {}


class UserResponse(UserBase):
    id: int
    google_linked: bool = False
    profile: Optional[UserProfileBase] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_google_linked(cls, data: Any) -> Any:
        """Derive google_linked from google_refresh_token presence."""
        if hasattr(data, "google_refresh_token"):
            # ORM object — read the token value safely
            token = getattr(data, "google_refresh_token", None)
            # Return a dict so Pydantic can set google_linked cleanly
            return {
                "id": data.id,
                "email": data.email,
                "username": data.username,
                "google_linked": token is not None and token != "",
                "profile": data.profile,
            }
        elif isinstance(data, dict):
            token = data.get("google_refresh_token")
            data["google_linked"] = token is not None and token != ""
        return data
