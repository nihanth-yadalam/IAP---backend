from enum import Enum
from typing import Dict
from pydantic import BaseModel, ConfigDict, field_validator


class Chronotype(str, Enum):
    morning_lark = "morning_lark"
    night_owl = "night_owl"
    neutral = "neutral"
    morning = "morning"
    evening = "evening"


class StudyStyle(str, Enum):
    pomodoro = "pomodoro"
    deep_work = "deep_work"


class OnboardingAnswers(BaseModel):
    chronotype: Chronotype
    study_style: StudyStyle
    subject_confidences: Dict[str, int]

    model_config = ConfigDict(extra="allow")

    @field_validator("subject_confidences")
    @classmethod
    def validate_confidence_scores(cls, v: Dict[str, int]) -> Dict[str, int]:
        for subject, score in v.items():
            if not (1 <= score <= 10):
                raise ValueError(
                    f"Confidence score for {subject} must be between 1 and 10"
                )
        return v
