from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

class Chronotype(str, Enum):
    morning = "morning"
    balanced = "balanced"
    night = "night"

class WorkStyle(str, Enum):
    deep = "deep"
    mixed = "mixed"
    sprints = "sprints"

class OnboardingAnswers(BaseModel):
    name: str = Field(..., description="Full name of the user")
    university: str = Field(..., description="University name")
    major: str = Field(..., description="Major subject")
    chronotype: Chronotype
    work_style: WorkStyle
    preferred_session_mins: int = Field(..., ge=15, le=180, description="Preferred study session length in minutes")

    model_config = ConfigDict(extra="allow")

    # Removed subject_confidences validator as it's no longer in the payload

