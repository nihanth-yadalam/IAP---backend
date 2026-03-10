"""
Duration Estimator — memory-aware AI duration prediction via Gemini 2.0 Flash.

Three functions:
  1. get_duration_estimation_context  — pull memory from DB
  2. build_duration_estimation_prompt — construct the Gemini prompt
  3. call_gemini_for_duration         — call Gemini, parse response
"""

from __future__ import annotations
import json
import logging
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Course
from app.models.user import UserProfile
from app.schemas.duration import DurationEstimationResponse

logger = logging.getLogger(__name__)


# ── 1. Memory Retrieval ──────────────────────────────────────────────


async def get_duration_estimation_context(
    user_id: int,
    course_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Query user memory and return a clean dict for the prompt builder.
    Raises HTTP 400 if memory not initialised, 404 if course memory missing.
    """
    # Fetch profile memory
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalars().first()

    if not profile or not profile.onboarding_data:
        raise HTTPException(
            status_code=400,
            detail="User profile memory is not initialized. Please complete onboarding.",
        )

    memory: dict = dict(profile.onboarding_data)

    # Fetch course name
    course_result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )
    course = course_result.scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course_key = str(course_id)
    subject_modifiers = memory.get("subject_modifiers", {})
    course_mem = subject_modifiers.get(course_key)

    if course_mem is None:
        raise HTTPException(
            status_code=404,
            detail="Course memory not found. Please ensure the course was created correctly.",
        )

    global_settings = memory.get("global_settings", {})
    behavioral_signals = memory.get("behavioral_signals", {})

    return {
        "course_name": course.name,
        "confidence_score": course_mem.get("confidence_score", 5),
        "duration_multiplier": course_mem.get("duration_multiplier", 1.0),
        "drain_rate": course_mem.get("drain_rate", 5),
        "session_count": course_mem.get("session_count", 0),
        "course_manual_rules": course_mem.get("manual_rules", []),
        "preferred_session_duration_mins": global_settings.get(
            "preferred_session_duration_mins", 50
        ),
        "procrastination_index": behavioral_signals.get("procrastination_index", 0.0),
        "generic_manual_rules": memory.get("manual_rules", []),
    }


# ── 2. Prompt Builder ───────────────────────────────────────────────


def build_duration_estimation_prompt(
    task_details: dict[str, Any],
    memory_context: dict[str, Any],
) -> str:
    """Build the full Gemini prompt from task details + user memory."""

    session_count = memory_context["session_count"]
    if session_count >= 10:
        reliability_note = "treat this as reliable"
    elif session_count >= 3:
        reliability_note = "treat this with moderate confidence, limited data"
    else:
        reliability_note = "treat this with caution, very limited data"

    course_rules = memory_context["course_manual_rules"]
    generic_rules = memory_context["generic_manual_rules"]
    course_rules_str = ", ".join(course_rules) if course_rules else "None"
    generic_rules_str = ", ".join(generic_rules) if generic_rules else "None"

    prompt = f"""You are an expert academic time estimator for a student planner. \
Your job is to predict how long a specific task will take THIS specific student, \
based on their personal performance history. \
Do not give a generic estimate — personalize it entirely to the data provided.

---

TASK DETAILS:
- Course: {memory_context["course_name"]}
- Task Type: {task_details["task_type"]}
- Difficulty: {task_details["difficulty"]}
- Description: {task_details["description"]}

---

STUDENT'S MEMORY FOR THIS COURSE:
- Confidence Score: {memory_context["confidence_score"]} / 10
- Historical Duration Multiplier: {memory_context["duration_multiplier"]}x
  (This means the student historically takes {memory_context["duration_multiplier"]}x longer \
than a typical estimate for this course. Based on {session_count} sessions — \
{reliability_note})
- Drain Rate: {memory_context["drain_rate"]} / 10

STUDENT'S GENERIC MEMORY:
- Preferred Session Length: {memory_context["preferred_session_duration_mins"]} mins
- Procrastination Index: {memory_context["procrastination_index"]} \
  (0 = never procrastinates, 1 = always delays. Add proportional buffer if above 0.5)

STUDENT'S PERSONAL RULES (must be respected):
- Course rules: {course_rules_str}
- Generic rules: {generic_rules_str}

---

INSTRUCTIONS:
1. Read the task description carefully and reason about its likely scope and complexity.
   Use your knowledge of academic tasks to form an initial estimate.
   Do not apply generic ranges — the description is your primary signal for scope.

2. Apply the student's duration_multiplier to your initial estimate.

3. If procrastination_index > 0.5, add a buffer:
   buffer = initial_estimate × (procrastination_index - 0.5) × 0.4

4. Apply any manual rules literally.

5. Round to the nearest 15 minutes.

GUARDRAILS (hard limits — never violate these):
- Minimum estimate: 15 mins
- Maximum estimate: 480 mins (8 hours)
- If your reasoning leads beyond 8 hours, cap at 480 and note in the reasoning \
  that this is a large task that should be broken into sub-tasks.
---

RESPONSE FORMAT:
Respond only in this exact JSON format, nothing else:
{{
  "estimated_duration_mins": 90,
  "reasoning": "One sentence explaining the key factors that drove this estimate."
}}

The reasoning must mention the duration multiplier and at least one other personalisation factor.
Do not use technical variable names in the reasoning. Write it for the student to read."""

    return prompt


# ── 3. Gemini Call ───────────────────────────────────────────────────


async def call_gemini_for_duration(prompt: str) -> DurationEstimationResponse:
    """
    Call Gemini 2.0 Flash, parse the JSON response, clamp duration, return schema.
    Raises HTTP 503 on any failure.
    """
    import asyncio

    try:
        from app.core.config import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        from google import genai

        client = genai.Client(api_key=api_key)

        # Run synchronous Gemini call in a thread with a 30s timeout
        def _call():
            return client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _call),
            timeout=30,
        )

        raw_text = response.text.strip()
        logger.info(f"[duration_estimator] Raw Gemini response: {raw_text[:500]}")

        # Defensively strip markdown fences
        cleaned = raw_text
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        # Clamp duration to [15, 480]
        duration = int(parsed["estimated_duration_mins"])
        duration = max(15, min(480, duration))

        reasoning = str(parsed.get("reasoning", "Estimate based on your study history."))

        return DurationEstimationResponse(
            estimated_duration_mins=duration,
            reasoning=reasoning,
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"[duration_estimator] JSON parse failed: {e}. Raw: {raw_text[:500] if 'raw_text' in dir() else 'N/A'}")
        raise HTTPException(
            status_code=503,
            detail="Duration estimation is temporarily unavailable. Please enter duration manually.",
        )
    except asyncio.TimeoutError:
        logger.error("[duration_estimator] Gemini call timed out (30s)")
        raise HTTPException(
            status_code=503,
            detail="Duration estimation is temporarily unavailable. Please enter duration manually.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[duration_estimator] Unexpected error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Duration estimation is temporarily unavailable. Please enter duration manually.",
        )
