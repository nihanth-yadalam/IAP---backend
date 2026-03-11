"""
Scheduler Service — AI-powered slot recommendation via Gemini 2.0 Flash.

Six functions:
  1. get_free_slots            — find available time gaps in the user's schedule
  2. get_daily_burnout_scores  — compute burnout for each day in the period
  3. filter_candidate_slots    — pre-filter and enrich slots before Gemini
  4. get_scheduling_context    — pull memory context from DB
  5. build_scheduling_prompt   — construct the Gemini prompt
  6. call_gemini_for_scheduling — call Gemini, parse and validate response
"""

from __future__ import annotations
import json
import logging
import math
import re
from collections import defaultdict
from datetime import date, time, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskLog, Course, TaskStatus
from app.models.schedule import FixedSlot
from app.models.user import UserProfile
from app.services.memory_calculator import get_time_block, compute_daily_burnout_score
from app.schemas.duration import RecommendedSlot, SlotRecommendationResponse

logger = logging.getLogger(__name__)

# Day-of-week names matching DayOfWeek enum
_WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

# Scheduling day boundaries
_DAY_START = time(7, 0)
_DAY_END = time(23, 0)


# ── 1. Free Slot Calculation ────────────────────────────────────────


async def get_free_slots(
    user_id: int,
    period_start: date,
    period_end: date,
    estimated_duration_mins: int,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """
    For each day in [period_start, period_end], find gaps >= estimated_duration_mins
    between 07:00 and 23:00 that are not occupied by fixed slots or scheduled tasks.
    """
    free_slots: list[dict] = []
    current_date = period_start

    while current_date <= period_end:
        day_name = _WEEKDAY_NAMES[current_date.weekday()]

        # 1a. Query recurring fixed slots for this day of week
        fixed_result = await db.execute(
            select(FixedSlot).where(
                FixedSlot.user_id == user_id,
                FixedSlot.day_of_week == day_name,
                FixedSlot.is_deleted == False,
            )
        )
        fixed_slots = fixed_result.scalars().all()

        # 1b. Query scheduled tasks on this date
        day_start_dt = datetime.combine(current_date, time(0, 0), tzinfo=timezone.utc)
        day_end_dt = datetime.combine(current_date + timedelta(days=1), time(0, 0), tzinfo=timezone.utc)

        task_result = await db.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.scheduled_start_time >= day_start_dt,
                Task.scheduled_start_time < day_end_dt,
                Task.status != TaskStatus.Completed,
            )
        )
        scheduled_tasks = task_result.scalars().all()

        # 2. Build sorted list of busy periods as (start_time, end_time)
        busy_periods: list[tuple[time, time]] = []

        for slot in fixed_slots:
            if slot.start_time is not None and slot.end_time is not None:
                busy_periods.append((slot.start_time, slot.end_time))
            else:
                logger.warning(f"[scheduler] Fixed slot {slot.id} has null times, skipping")

        for task in scheduled_tasks:
            if task.scheduled_start_time and task.scheduled_end_time:
                busy_periods.append((
                    task.scheduled_start_time.time(),
                    task.scheduled_end_time.time(),
                ))
            else:
                logger.warning(f"[scheduler] Task {task.id} has partial schedule, skipping")

        busy_periods.sort(key=lambda x: x[0])

        # 3. Find gaps between 07:00 and 23:00
        gaps = _find_gaps(busy_periods, _DAY_START, _DAY_END)

        # 4. Keep only gaps >= estimated_duration_mins
        for gap_start, gap_end in gaps:
            gap_mins = _time_diff_mins(gap_start, gap_end)
            if gap_mins >= estimated_duration_mins:
                hour = gap_start.hour
                free_slots.append({
                    "day": day_name,
                    "date": current_date,
                    "start_time": gap_start,
                    "end_time": gap_end,
                    "time_block": get_time_block(hour),
                    "available_duration_mins": gap_mins,
                })

        current_date += timedelta(days=1)

    return free_slots


def _find_gaps(
    busy_periods: list[tuple[time, time]],
    day_start: time,
    day_end: time,
) -> list[tuple[time, time]]:
    """Find free gaps in the day not covered by busy periods."""
    gaps = []
    cursor = day_start

    for start, end in busy_periods:
        # Skip busy periods outside our window
        if end <= day_start or start >= day_end:
            continue
        # Clamp to day window
        effective_start = max(start, day_start)
        effective_end = min(end, day_end)

        if effective_start > cursor:
            gaps.append((cursor, effective_start))
        cursor = max(cursor, effective_end)

    # Gap after last busy period
    if cursor < day_end:
        gaps.append((cursor, day_end))

    return gaps


def _time_diff_mins(t1: time, t2: time) -> int:
    """Calculate minutes between two time objects."""
    return (t2.hour * 60 + t2.minute) - (t1.hour * 60 + t1.minute)


# ── 2. Daily Burnout Scores ─────────────────────────────────────────


async def get_daily_burnout_scores(
    user_id: int,
    period_start: date,
    period_end: date,
    db: AsyncSession,
) -> dict[date, dict[str, Any]]:
    """
    For each day in [period_start, period_end], compute a burnout score
    using compute_daily_burnout_score().
    """
    # Load user memory once
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalars().first()
    if not profile or not profile.onboarding_data:
        return {}

    memory = dict(profile.onboarding_data)
    subject_modifiers = memory.get("subject_modifiers", {})
    time_block_stats = memory.get("time_block_stats", {})

    # Compute max_daily_load from 90-day history (90th percentile)
    max_daily_load = await _compute_max_daily_load(
        user_id, subject_modifiers, time_block_stats, db
    )

    scores: dict[date, dict] = {}
    current_date = period_start

    while current_date <= period_end:
        # Scheduled tasks for this day
        day_start_dt = datetime.combine(current_date, time(0, 0), tzinfo=timezone.utc)
        day_end_dt = datetime.combine(current_date + timedelta(days=1), time(0, 0), tzinfo=timezone.utc)

        task_result = await db.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.scheduled_start_time >= day_start_dt,
                Task.scheduled_start_time < day_end_dt,
                Task.status != TaskStatus.Completed,
            )
        )
        day_tasks = task_result.scalars().all()

        scheduled_task_dicts = []
        for t in day_tasks:
            if t.scheduled_start_time:
                scheduled_task_dicts.append({
                    "scheduled_start_hour": t.scheduled_start_time.hour,
                    "estimated_duration_mins": t.estimated_duration_mins or 30,
                    "course_id": t.course_id or 0,
                })

        # Recent logs for last 5 days before current_date
        recent_logs_5_days = []
        for i in range(1, 6):
            log_date = current_date - timedelta(days=i)
            log_start = datetime.combine(log_date, time(0, 0), tzinfo=timezone.utc)
            log_end = datetime.combine(log_date + timedelta(days=1), time(0, 0), tzinfo=timezone.utc)

            log_result = await db.execute(
                select(TaskLog).where(
                    TaskLog.user_id == user_id,
                    TaskLog.completion_time >= log_start,
                    TaskLog.completion_time < log_end,
                )
            )
            day_logs = log_result.scalars().all()
            recent_logs_5_days.append(
                [{"drain_intensity": l.drain_intensity} for l in day_logs]
            )

        score = compute_daily_burnout_score(
            scheduled_tasks=scheduled_task_dicts,
            course_memory=subject_modifiers,
            time_block_stats=time_block_stats,
            recent_logs_5_days=recent_logs_5_days,
            max_daily_load=max_daily_load,
        )

        scores[current_date] = {
            "score": round(score, 2),
            "label": _burnout_label(score),
        }

        current_date += timedelta(days=1)

    return scores


async def _compute_max_daily_load(
    user_id: int,
    subject_modifiers: dict,
    time_block_stats: dict,
    db: AsyncSession,
) -> float:
    """Compute the 90th percentile of daily projected load over last 90 days."""
    ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)

    log_result = await db.execute(
        select(TaskLog, Task)
        .join(Task, TaskLog.task_id == Task.id)
        .where(
            TaskLog.user_id == user_id,
            TaskLog.completion_time >= ninety_days_ago,
        )
    )
    rows = log_result.all()

    if len(rows) < 10:
        return 4.0  # default for sparse data

    # Group by date
    daily_loads: dict[date, float] = defaultdict(float)
    for log, task in rows:
        log_date = log.completion_time.date()
        block = get_time_block(log.completion_time.hour)
        block_stats = time_block_stats.get(block, {})
        block_productivity = block_stats.get("productivity_score", 0.5)
        time_block_weight = 1 + (1 - block_productivity)

        course_id_str = str(task.course_id) if task.course_id else "0"
        course_data = subject_modifiers.get(course_id_str, {})
        course_drain = course_data.get("drain_rate", 5) / 10

        task_load = (log.actual_duration_mins / 60) * course_drain * time_block_weight
        daily_loads[log_date] += task_load

    if not daily_loads:
        return 4.0

    load_values = sorted(daily_loads.values())
    # 90th percentile using linear interpolation
    idx = 0.9 * (len(load_values) - 1)
    lower = int(math.floor(idx))
    upper = min(lower + 1, len(load_values) - 1)
    frac = idx - lower
    return load_values[lower] + frac * (load_values[upper] - load_values[lower])


def _burnout_label(score: float) -> str:
    if score <= 0.25:
        return "fresh"
    elif score <= 0.50:
        return "moderate"
    elif score <= 0.75:
        return "loaded"
    else:
        return "critical"


# ── 3. Pre-filtering Candidate Slots ────────────────────────────────


def filter_candidate_slots(
    free_slots: list[dict],
    burnout_scores: dict[date, dict],
    course_memory: dict[str, Any],
    user_memory: dict[str, Any],
) -> list[dict]:
    """
    Pre-filter and enrich free slots before sending to Gemini.
    Removes clearly unsuitable slots, enriches the rest with performance data.
    """
    time_block_stats = user_memory.get("time_block_stats", {})
    tba = course_memory.get("time_block_affinity", {})
    drain_rate = course_memory.get("drain_rate", 5)

    candidates = []
    for slot in free_slots:
        slot_date = slot["date"]
        block = slot["time_block"]
        burnout = burnout_scores.get(slot_date, {"score": 0.0, "label": "fresh"})

        # Filter 1: Critical burnout + high drain hard block
        if burnout["label"] == "critical" and drain_rate > 7:
            continue

        # Filter 2: Zero history block with weak global productivity
        course_block = tba.get(block, {})
        global_block = time_block_stats.get(block, {})
        if (
            course_block.get("sample_count", 0) == 0
            and global_block.get("productivity_score", 0.5) < 0.3
        ):
            continue

        # Enrich with performance data
        slot["burnout_score"] = burnout["score"]
        slot["burnout_label"] = burnout["label"]
        slot["course_block_completion_rate"] = round(
            course_block.get("completion_rate", 0.5), 2
        )
        slot["course_block_avg_drain"] = round(
            course_block.get("avg_drain", 0.5), 2
        )
        slot["course_block_duration_ratio"] = round(
            course_block.get("duration_ratio", 1.0), 2
        )
        slot["course_block_sample_count"] = course_block.get("sample_count", 0)

        candidates.append(slot)

    return candidates


# ── 4. Scheduling Context Retrieval ─────────────────────────────────


async def get_scheduling_context(
    user_id: int,
    course_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Pull everything the scheduling prompt needs from the database.
    """
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalars().first()

    if not profile or not profile.onboarding_data:
        raise HTTPException(
            status_code=400,
            detail="User profile memory is not initialized. Please complete onboarding.",
        )

    memory = dict(profile.onboarding_data)

    # Course name
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
        "drain_rate": course_mem.get("drain_rate", 5),
        "course_memory": course_mem,
        "time_block_stats": memory.get("time_block_stats", {}),
        "chronotype": global_settings.get("chronotype", "unknown"),
        "current_archetype": getattr(profile, "current_archetype", "Unclassified") or "Unclassified",
        "procrastination_index": round(behavioral_signals.get("procrastination_index", 0.0), 2),
        "burnout_risk_score": round(behavioral_signals.get("burnout_risk_score", 0.0), 2),
        "course_manual_rules": course_mem.get("manual_rules", []),
        "generic_manual_rules": memory.get("manual_rules", []),
    }


# ── 5. Prompt Builder ───────────────────────────────────────────────


def build_scheduling_prompt(
    task_details: dict[str, Any],
    candidate_slots: list[dict],
    memory_context: dict[str, Any],
    estimated_duration_mins: int,
) -> str:
    """Build the full Gemini scheduling prompt."""

    tbs = memory_context["time_block_stats"]

    def _block_stat(block: str, key: str, default: float = 0.5) -> str:
        return str(round(tbs.get(block, {}).get(key, default), 2))

    # Format candidate slots
    slot_lines = []
    for i, slot in enumerate(candidate_slots, 1):
        # Calculate task end_time = start_time + estimated_duration_mins
        start_dt = datetime.combine(date.today(), slot["start_time"])
        end_dt = start_dt + timedelta(minutes=estimated_duration_mins)
        task_end = end_dt.time()

        slot_lines.append(
            f"- Slot {i}: {slot['day']}, {slot['date']}, "
            f"{slot['start_time'].strftime('%H:%M')} – {task_end.strftime('%H:%M')}\n"
            f"  | Time Block: {slot['time_block']}\n"
            f"  | Day Burnout Level: {slot['burnout_score']} ({slot['burnout_label']})\n"
            f"  | Course performance in this block: \n"
            f"      completion_rate: {slot['course_block_completion_rate']}, \n"
            f"      avg_drain: {slot['course_block_avg_drain']}, \n"
            f"      duration_ratio: {slot['course_block_duration_ratio']},\n"
            f"      data confidence: {slot['course_block_sample_count']} sessions"
        )
    slots_text = "\n\n".join(slot_lines)

    course_rules = memory_context["course_manual_rules"]
    generic_rules = memory_context["generic_manual_rules"]
    course_rules_str = ", ".join(course_rules) if course_rules else "None"
    generic_rules_str = ", ".join(generic_rules) if generic_rules else "None"

    prompt = f"""You are an intelligent academic scheduler for a student planner.
Your job is to recommend one or more best time slots to schedule a specific task
for this specific student, based on their performance history, energy patterns,
and personal rules.

Rank the slots from best to worst. Be specific about why each slot was chosen
or ranked the way it was.

---

TASK TO SCHEDULE:
- Course: {memory_context["course_name"]}
- Task Type: {task_details["task_type"]}
- Difficulty: {task_details["difficulty"]}
- Description: {task_details["description"]}
- Estimated Duration: {estimated_duration_mins} mins
- Drain Rate for this course: {memory_context["drain_rate"]} / 10

---

CANDIDATE FREE SLOTS:
(These are the only slots available within the student's requested time period.
 Slots that were too short or clearly unsuitable have already been removed.)

{slots_text}

---

STUDENT'S ENERGY PROFILE:
Time block productivity scores (higher = student performs better):
- Morning   (06:00–12:00): {_block_stat("morning", "productivity_score")}   | avg drain: {_block_stat("morning", "avg_drain")}
- Afternoon (12:00–17:00): {_block_stat("afternoon", "productivity_score")}  | avg drain: {_block_stat("afternoon", "avg_drain")}
- Evening   (17:00–00:00): {_block_stat("evening", "productivity_score")}    | avg drain: {_block_stat("evening", "avg_drain")}
- Night     (00:00–06:00): {_block_stat("night", "productivity_score")}      | avg drain: {_block_stat("night", "avg_drain")}

Chronotype: {memory_context["chronotype"]}
Current Persona: {memory_context["current_archetype"]}
Procrastination Index: {memory_context["procrastination_index"]} (0 = never, 1 = always)
Burnout Risk: {memory_context["burnout_risk_score"]} (0 = safe, 1 = critical)

---

STUDENT'S PERSONAL RULES (must be respected absolutely):
- Generic rules: {generic_rules_str}
- Rules for {memory_context["course_name"]}: {course_rules_str}

---

INSTRUCTIONS:
1. Evaluate each candidate slot against the student's energy profile and
   course-specific block performance.

2. Prefer slots where:
   - The time block has high productivity_score for this student
   - The course's completion_rate in that block is high
   - The day burnout level is 'fresh' or 'moderate'
   - The slot does not immediately follow another high drain task

3. Penalise slots where:
   - Day burnout label is 'loaded' or 'critical'
   - The course's avg_drain in that block is above 0.7

4. Respect the persona:
   - 'The Night Owl': prefer evening/night blocks, deprioritise morning slots
   - 'The Early Bird': prefer morning blocks, deprioritise evening slots
   - 'The Procrastinator': prefer the earliest viable slot, add a note encouraging early start
   - 'The Dedicated Star': trust the productivity scores, no special adjustment needed
   - 'Unclassified': rely purely on productivity scores and burnout levels

5. Apply all personal rules literally — they override everything else.

6. If course-specific block data has fewer than 3 sessions (low confidence),
   fall back to the global time block productivity scores for that block.

7. Recommend between 2 and 3 slots. Never recommend only 1 unless only 1 candidate
   exists. Never recommend more than 3.

---

RESPONSE FORMAT:
Respond only in this exact JSON format. No markdown, no backticks, no text outside the JSON:
{{
  "recommendations": [
    {{
      "rank": 1,
      "day": "Monday",
      "date": "2025-03-17",
      "start_time": "19:00",
      "end_time": "20:30",
      "time_block": "evening",
      "reasoning": "One sentence explaining why this is the best slot for this student."
    }},
    {{
      "rank": 2,
      "day": "Wednesday",
      "date": "2025-03-19",
      "start_time": "09:00",
      "end_time": "10:30",
      "time_block": "morning",
      "reasoning": "One sentence explaining why this is the second choice."
    }}
  ],
  "scheduling_note": "One optional sentence of broader advice, e.g. flagging high burnout risk this week or suggesting breaking the task into sub-tasks."
}}

Reasoning must be written for the student to read directly.
Do not use technical variable names like 'productivity_score' or 'duration_ratio'.
Do not repeat the same reasoning across slots — each must explain its own distinct merit."""

    return prompt


# ── 6. Gemini Call for Scheduling ────────────────────────────────────


async def call_gemini_for_scheduling(
    prompt: str,
    estimated_duration_mins: int,
    period_start: date,
    period_end: date,
) -> SlotRecommendationResponse:
    """
    Call Gemini 2.0 Flash for scheduling recommendations.
    Validates and corrects the response before returning.
    """
    import asyncio

    raw_text = ""
    try:
        from app.core.config import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        from google import genai

        client = genai.Client(api_key=api_key)

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
        logger.info(f"[scheduler] Raw Gemini response: {raw_text[:500]}")

        # Defensively strip markdown fences
        cleaned = raw_text
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        # Validate and build recommendations
        valid_recs: list[RecommendedSlot] = []
        for rec in parsed.get("recommendations", []):
            try:
                rec_date = date.fromisoformat(rec["date"])

                # Validate date is within period
                if rec_date < period_start or rec_date > period_end:
                    logger.warning(f"[scheduler] Recommendation date {rec_date} outside period, dropping")
                    continue

                start_t = time.fromisoformat(rec["start_time"])

                # Recalculate end_time from start_time + duration (never trust Gemini's end_time)
                start_dt = datetime.combine(rec_date, start_t)
                end_dt = start_dt + timedelta(minutes=estimated_duration_mins)
                end_t = end_dt.time()

                valid_recs.append(RecommendedSlot(
                    rank=len(valid_recs) + 1,  # reindex
                    day=rec.get("day", _WEEKDAY_NAMES[rec_date.weekday()]),
                    date=rec_date,
                    start_time=start_t,
                    end_time=end_t,
                    time_block=rec.get("time_block", get_time_block(start_t.hour)),
                    reasoning=rec.get("reasoning", "Recommended based on your study patterns."),
                ))
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"[scheduler] Skipping invalid recommendation: {e}")
                continue

        if len(valid_recs) < 1:
            raise HTTPException(
                status_code=503,
                detail="Scheduling is temporarily unavailable. Please select a slot manually.",
            )

        scheduling_note = parsed.get("scheduling_note")

        return SlotRecommendationResponse(
            recommendations=valid_recs[:3],
            scheduling_note=scheduling_note,
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"[scheduler] JSON parse failed: {e}. Raw: {raw_text[:500]}")
        raise HTTPException(
            status_code=503,
            detail="Scheduling is temporarily unavailable. Please select a slot manually.",
        )
    except asyncio.TimeoutError:
        logger.error("[scheduler] Gemini call timed out (30s)")
        raise HTTPException(
            status_code=503,
            detail="Scheduling is temporarily unavailable. Please select a slot manually.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[scheduler] Unexpected error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Scheduling is temporarily unavailable. Please select a slot manually.",
        )
