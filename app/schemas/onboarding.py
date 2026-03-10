from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class OnboardingAnswers(BaseModel):
    """
    Flexible onboarding questionnaire answers.
    All fields are optional so the frontend can send any subset.
    Unknown fields are allowed via extra="allow".
    """
    # Profile fields
    name: Optional[str] = None
    university: Optional[str] = None
    major: Optional[str] = None

    # Preference fields (flexible strings — not strict enums)
    chronotype: Optional[str] = None        # e.g. "morning_lark", "morning", "night_owl", "night"
    work_style: Optional[str] = None        # e.g. "deep", "mixed", "sprints"
    study_style: Optional[str] = None       # alias for work_style from some frontends
    preferred_session_mins: Optional[int] = Field(None, ge=15, le=360)
    subject_confidences: Optional[Dict[str, Any]] = None  # e.g. {"Math": 7, "Physics": 5}

    model_config = ConfigDict(extra="allow")
