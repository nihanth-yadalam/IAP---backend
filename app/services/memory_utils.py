"""
JSONB Memory Utilities — initialize and update the AI memory structure
stored in user_profiles.onboarding_data.

IMPORTANT: All JSONB updates use PostgreSQL's || merge operator via
raw SQL to avoid race conditions from read-modify-write in Python.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _default_time_block_entry() -> dict:
    """Neutral defaults for a time-block stats entry."""
    return {
        "productivity_score": 0.5,
        "avg_drain": 0.5,
        "completion_rate": 0.5,
        "sample_count": 0,
    }


def _default_course_time_block_entry() -> dict:
    """Neutral defaults for course-level time-block affinity."""
    return {
        "duration_ratio": 1.0,
        "avg_drain": 0.5,
        "completion_rate": 0.5,
        "sample_count": 0,
    }


def build_initial_memory(
    chronotype: str,
    base_energy_level: int,
    preferred_session_duration_mins: int,
) -> dict:
    """Build the full initial memory JSONB structure (called at onboarding)."""
    return {
        "global_settings": {
            "chronotype": chronotype,
            "base_energy_level": base_energy_level,
            "preferred_session_duration_mins": preferred_session_duration_mins,
        },
        "time_block_stats": {
            "morning": _default_time_block_entry(),
            "afternoon": _default_time_block_entry(),
            "evening": _default_time_block_entry(),
            "night": _default_time_block_entry(),
        },
        "behavioral_signals": {
            "procrastination_index": 0.0,
            "burnout_risk_score": 0.0,
            "consistency_score": 0.5,
            "streak_days": 0,
        },
        "manual_rules": [],
        "subject_modifiers": {},
    }


def build_course_memory_entry(
    confidence_score: int = 5,
    drain_rate: int = 5,
) -> dict:
    """Build a single course entry for subject_modifiers."""
    return {
        "confidence_score": confidence_score,
        "duration_multiplier": 1.0,
        "drain_rate": drain_rate,
        "session_count": 0,
        "early_finish_rate": 0.0,
        "time_block_affinity": {
            "morning": _default_course_time_block_entry(),
            "afternoon": _default_course_time_block_entry(),
            "evening": _default_course_time_block_entry(),
            "night": _default_course_time_block_entry(),
        },
        "manual_rules": [],
    }


async def initialize_memory(
    db: AsyncSession,
    user_id: int,
    chronotype: str,
    base_energy_level: int,
    preferred_session_duration_mins: int,
) -> None:
    """
    Initialize the AI memory JSONB on user_profiles.onboarding_data.
    Uses PostgreSQL || merge so existing keys are preserved.
    """
    import json

    memory = build_initial_memory(
        chronotype=chronotype,
        base_energy_level=base_energy_level,
        preferred_session_duration_mins=preferred_session_duration_mins,
    )

    await db.execute(
        text(
            """
            UPDATE user_profiles
            SET onboarding_data = COALESCE(onboarding_data, '{}'::jsonb) || :memory_json::jsonb
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id, "memory_json": json.dumps(memory)},
    )
    await db.flush()


async def add_course_memory(
    db: AsyncSession,
    user_id: int,
    course_id: int,
    confidence_score: int = 5,
    drain_rate: int = 5,
) -> None:
    """
    Add a course entry to subject_modifiers in the AI memory JSONB.
    Uses jsonb_set for targeted path update instead of full overwrite.
    """
    import json

    entry = build_course_memory_entry(
        confidence_score=confidence_score,
        drain_rate=drain_rate,
    )

    course_key = str(course_id)

    await db.execute(
        text(
            """
            UPDATE user_profiles
            SET onboarding_data = jsonb_set(
                COALESCE(onboarding_data, '{}'::jsonb),
                ARRAY['subject_modifiers', :course_key],
                :entry_json::jsonb,
                true
            )
            WHERE user_id = :user_id
            """
        ),
        {
            "user_id": user_id,
            "course_key": course_key,
            "entry_json": json.dumps(entry),
        },
    )
    await db.flush()
