"""
Memory Calculator — pure functions only (no DB, no API calls).

Every function takes plain data and returns a computed value.
Used by the reflexion agent and scheduler.
"""

from __future__ import annotations
import math
import statistics
from datetime import date, timedelta
from typing import Any


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


# ─── Time Blocks ─────────────────────────────────────────────────────


def get_time_block(hour: int) -> str:
    """
    Map an hour (0–23) to a time block label.
    00-05 → 'night' | 06-11 → 'morning' | 12-16 → 'afternoon' | 17-23 → 'evening'
    """
    if 0 <= hour <= 5:
        return "night"
    elif 6 <= hour <= 11:
        return "morning"
    elif 12 <= hour <= 16:
        return "afternoon"
    else:  # 17-23
        return "evening"


# ─── Productivity Score ──────────────────────────────────────────────


def compute_productivity_score(
    completion_rate: float,
    avg_drain_normalized: float,
    duration_ratio: float,
) -> float:
    """
    Composite productivity score.

    score = (completion_rate × 0.40)
          + ((1 - avg_drain_normalized) × 0.30)
          + ((1 - clamp(duration_ratio - 1, 0, 1)) × 0.30)

    avg_drain_normalized is drain already divided by 10.
    Result clamped to [0, 1].
    """
    overtime_penalty = _clamp(duration_ratio - 1, 0, 1)
    score = (
        completion_rate * 0.40
        + (1 - avg_drain_normalized) * 0.30
        + (1 - overtime_penalty) * 0.30
    )
    return _clamp(score, 0, 1)


# ─── Weighted Average (Exponential Blending) ─────────────────────────


def compute_weighted_average(
    old_value: float,
    new_value: float,
    new_sample_count: int,
) -> float:
    """
    Core blending function for reflexion agent updates.

    α = 0.3 × clamp(new_sample_count / 10, 0.5, 1.5)
    result = (1 - α) × old_value + α × new_value
    Clamped to [0, 1].
    """
    alpha = 0.3 * _clamp(new_sample_count / 10, 0.5, 1.5)
    result = (1 - alpha) * old_value + alpha * new_value
    return _clamp(result, 0, 1)


# ─── Procrastination Index ───────────────────────────────────────────


def compute_procrastination_index(
    logs_with_task_data: list[dict[str, Any]],
    preferred_session_duration_mins: int,
) -> float:
    """
    Measures how long users wait before doing tasks.

    For each log:
        gap = (completion_time - task.created_at) in minutes - actual_duration_mins

    procrastination_index = avg_gap / preferred_session_duration_mins
    Clamped to [0, 1].

    Each entry in logs_with_task_data must have keys:
        'completion_time_ts' (float, epoch seconds),
        'created_at_ts' (float, epoch seconds),
        'actual_duration_mins' (int)
    """
    if not logs_with_task_data or preferred_session_duration_mins <= 0:
        return 0.0

    gaps = []
    for log in logs_with_task_data:
        total_elapsed_mins = (log["completion_time_ts"] - log["created_at_ts"]) / 60
        gap = total_elapsed_mins - log["actual_duration_mins"]
        gaps.append(max(gap, 0))

    avg_gap = sum(gaps) / len(gaps)
    return _clamp(avg_gap / preferred_session_duration_mins, 0, 1)


# ─── Burnout Risk ────────────────────────────────────────────────────


def compute_burnout_risk(logs_last_7_days: list[dict[str, Any]]) -> float:
    """
    high_drain_count = count of logs where drain_intensity >= 8
    total = len(logs_last_7_days)
    burnout_risk = high_drain_count / total   (0.0 if total == 0)
    """
    if not logs_last_7_days:
        return 0.0

    high_drain_count = sum(
        1 for log in logs_last_7_days if log["drain_intensity"] >= 8
    )
    return high_drain_count / len(logs_last_7_days)


# ─── Consistency Score ───────────────────────────────────────────────


def compute_consistency_score(daily_task_counts: list[int]) -> float:
    """
    Input: 30 integers — completed task count per day for last 30 days.

    mean = average(daily_task_counts)
    std_dev = standard_deviation(daily_task_counts)
    consistency_score = 1 - (std_dev / mean)   (0.0 if mean == 0)
    Clamped to [0, 1].
    """
    if not daily_task_counts:
        return 0.0

    mean = sum(daily_task_counts) / len(daily_task_counts)
    if mean == 0:
        return 0.0

    # Population standard deviation
    variance = sum((x - mean) ** 2 for x in daily_task_counts) / len(daily_task_counts)
    std_dev = math.sqrt(variance)

    return _clamp(1 - (std_dev / mean), 0, 1)


# ─── Streak Days ─────────────────────────────────────────────────────


def compute_streak_days(log_dates: list[date], today: date) -> int:
    """
    Walk backwards from today. Count consecutive days that have at least
    one log. Stop at the first day with no logs.
    """
    if not log_dates:
        return 0

    log_date_set = set(log_dates)
    streak = 0
    current = today

    while current in log_date_set:
        streak += 1
        current -= timedelta(days=1)

    return streak


# ─── Daily Burnout Score ─────────────────────────────────────────────


def compute_daily_burnout_score(
    scheduled_tasks: list[dict[str, Any]],
    course_memory: dict[str, Any],
    time_block_stats: dict[str, Any],
    recent_logs_5_days: list[list[dict[str, Any]]],
    max_daily_load: float,
) -> float:
    """
    Combines projected load (forward-looking) and cumulative fatigue (backward-looking).

    scheduled_tasks: list of dicts with keys:
        'scheduled_start_hour' (int), 'estimated_duration_mins' (int), 'course_id' (int|str)

    course_memory: the subject_modifiers dict

    time_block_stats: the global time_block_stats dict

    recent_logs_5_days: list of 5 lists (index 0 = yesterday, 4 = 5 days ago).
        Each inner list contains dicts with 'drain_intensity' (int).

    max_daily_load: normalizer for projected load.

    Returns: daily_burnout_score in [0, 1].
    """
    # ── Projected load ──
    projected_load = 0.0
    for task in scheduled_tasks:
        block = get_time_block(task["scheduled_start_hour"])
        block_stats = time_block_stats.get(block, {})
        block_productivity = block_stats.get("productivity_score", 0.5)
        time_block_weight = 1 + (1 - block_productivity)

        course_id_str = str(task["course_id"])
        course_data = course_memory.get(course_id_str, {})
        course_drain = course_data.get("drain_rate", 5) / 10

        task_load = (task["estimated_duration_mins"] / 60) * course_drain * time_block_weight
        projected_load += task_load

    if max_daily_load > 0:
        projected_load_normalized = _clamp(projected_load / max_daily_load, 0, 1)
    else:
        projected_load_normalized = 0.0

    # ── Cumulative fatigue ──
    decay_weights = [1.0, 0.65, 0.42, 0.27, 0.18]
    normalizer = 2.52
    weighted = 0.0

    for i, day_logs in enumerate(recent_logs_5_days):
        if i >= len(decay_weights):
            break
        if day_logs:
            day_drain = sum(
                log["drain_intensity"] / 10 for log in day_logs
            ) / len(day_logs)
        else:
            day_drain = 0.0
        weighted += day_drain * decay_weights[i]

    cumulative_fatigue = weighted / normalizer if normalizer > 0 else 0.0

    # ── Final score ──
    daily_burnout_score = (projected_load_normalized * 0.60) + (cumulative_fatigue * 0.40)
    return _clamp(daily_burnout_score, 0, 1)
