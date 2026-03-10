"""
Unit tests for app.services.memory_calculator — all pure functions.
"""

import math
from datetime import date, timedelta

import pytest
from app.services.memory_calculator import (
    get_time_block,
    compute_productivity_score,
    compute_weighted_average,
    compute_procrastination_index,
    compute_burnout_risk,
    compute_consistency_score,
    compute_streak_days,
    compute_daily_burnout_score,
)


# ── get_time_block ───────────────────────────────────────────────────

class TestGetTimeBlock:
    def test_night_hours(self):
        for h in range(0, 6):
            assert get_time_block(h) == "night", f"Hour {h} should be night"

    def test_morning_hours(self):
        for h in range(6, 12):
            assert get_time_block(h) == "morning", f"Hour {h} should be morning"

    def test_afternoon_hours(self):
        for h in range(12, 17):
            assert get_time_block(h) == "afternoon", f"Hour {h} should be afternoon"

    def test_evening_hours(self):
        for h in range(17, 24):
            assert get_time_block(h) == "evening", f"Hour {h} should be evening"

    def test_boundary_0(self):
        assert get_time_block(0) == "night"

    def test_boundary_5(self):
        assert get_time_block(5) == "night"

    def test_boundary_6(self):
        assert get_time_block(6) == "morning"

    def test_boundary_11(self):
        assert get_time_block(11) == "morning"

    def test_boundary_12(self):
        assert get_time_block(12) == "afternoon"

    def test_boundary_16(self):
        assert get_time_block(16) == "afternoon"

    def test_boundary_17(self):
        assert get_time_block(17) == "evening"

    def test_boundary_23(self):
        assert get_time_block(23) == "evening"


# ── compute_productivity_score ───────────────────────────────────────

class TestComputeProductivityScore:
    def test_perfect_scores(self):
        score = compute_productivity_score(1.0, 0.0, 1.0)
        assert score == pytest.approx(1.0)

    def test_worst_scores(self):
        score = compute_productivity_score(0.0, 1.0, 2.0)
        assert score == pytest.approx(0.0)

    def test_neutral_scores(self):
        score = compute_productivity_score(0.5, 0.5, 1.0)
        # 0.5*0.4 + 0.5*0.3 + 1.0*0.3 = 0.2 + 0.15 + 0.3 = 0.65
        assert score == pytest.approx(0.65)

    def test_overtime_penalty_clamped(self):
        # duration_ratio=3.0 → overtime_penalty = clamp(2.0, 0, 1) = 1.0
        score = compute_productivity_score(1.0, 0.0, 3.0)
        # 1.0*0.4 + 1.0*0.3 + (1-1.0)*0.3 = 0.4 + 0.3 + 0.0 = 0.7
        assert score == pytest.approx(0.7)

    def test_early_finish(self):
        # duration_ratio=0.5 → overtime_penalty = clamp(-0.5, 0, 1) = 0.0
        score = compute_productivity_score(0.8, 0.3, 0.5)
        # 0.8*0.4 + 0.7*0.3 + 1.0*0.3 = 0.32 + 0.21 + 0.3 = 0.83
        assert score == pytest.approx(0.83)

    def test_result_clamped_to_0_1(self):
        score = compute_productivity_score(0.0, 1.0, 2.0)
        assert 0.0 <= score <= 1.0


# ── compute_weighted_average ─────────────────────────────────────────

class TestComputeWeightedAverage:
    def test_basic_blend(self):
        result = compute_weighted_average(0.5, 1.0, 10)
        # α = 0.3 * clamp(10/10, 0.5, 1.5) = 0.3 * 1.0 = 0.3
        # result = 0.7 * 0.5 + 0.3 * 1.0 = 0.35 + 0.30 = 0.65
        assert result == pytest.approx(0.65)

    def test_small_sample_count(self):
        result = compute_weighted_average(0.5, 1.0, 2)
        # α = 0.3 * clamp(2/10, 0.5, 1.5) = 0.3 * 0.5 = 0.15
        # result = 0.85 * 0.5 + 0.15 * 1.0 = 0.425 + 0.15 = 0.575
        assert result == pytest.approx(0.575)

    def test_large_sample_count(self):
        result = compute_weighted_average(0.5, 1.0, 20)
        # α = 0.3 * clamp(20/10, 0.5, 1.5) = 0.3 * 1.5 = 0.45
        # result = 0.55 * 0.5 + 0.45 * 1.0 = 0.275 + 0.45 = 0.725
        assert result == pytest.approx(0.725)

    def test_result_clamped_at_0(self):
        result = compute_weighted_average(0.0, -1.0, 10)
        assert result == 0.0

    def test_result_clamped_at_1(self):
        result = compute_weighted_average(1.0, 2.0, 10)
        assert result == 1.0

    def test_no_change_when_same(self):
        result = compute_weighted_average(0.5, 0.5, 10)
        assert result == pytest.approx(0.5)


# ── compute_procrastination_index ────────────────────────────────────

class TestComputeProcrastinationIndex:
    def test_empty_logs(self):
        assert compute_procrastination_index([], 50) == 0.0

    def test_zero_session_duration(self):
        assert compute_procrastination_index([{"completion_time_ts": 1000, "scheduled_start_ts": 0, "actual_duration_mins": 10}], 0) == 0.0

    def test_no_procrastination(self):
        # Task scheduled and immediately worked on
        logs = [{
            "completion_time_ts": 3600,  # 60 mins after schedule
            "scheduled_start_ts": 0,
            "actual_duration_mins": 60,
        }]
        result = compute_procrastination_index(logs, 50)
        assert result == pytest.approx(0.0)

    def test_moderate_procrastination(self):
        # 60 min total, 30 min actual → 30 min gap
        logs = [{
            "completion_time_ts": 3600,
            "scheduled_start_ts": 0,
            "actual_duration_mins": 30,
        }]
        # gap = 60 - 30 = 30, index = 30/50 = 0.6
        result = compute_procrastination_index(logs, 50)
        assert result == pytest.approx(0.6)

    def test_clamped_at_1(self):
        logs = [{
            "completion_time_ts": 36000,  # 600 mins
            "scheduled_start_ts": 0,
            "actual_duration_mins": 30,
        }]
        result = compute_procrastination_index(logs, 50)
        assert result == 1.0

    def test_missing_scheduled_time_ignored(self):
        logs = [{
            "completion_time_ts": 36000, 
            "scheduled_start_ts": None,
            "actual_duration_mins": 30,
        }]
        result = compute_procrastination_index(logs, 50)
        assert result == 0.0


# ── compute_burnout_risk ─────────────────────────────────────────────

class TestComputeBurnoutRisk:
    def test_empty_logs(self):
        assert compute_burnout_risk([]) == 0.0

    def test_no_high_drain(self):
        logs = [{"drain_intensity": 5}, {"drain_intensity": 3}, {"drain_intensity": 7}]
        assert compute_burnout_risk(logs) == 0.0

    def test_all_high_drain(self):
        logs = [{"drain_intensity": 8}, {"drain_intensity": 9}, {"drain_intensity": 10}]
        assert compute_burnout_risk(logs) == 1.0

    def test_mixed(self):
        logs = [
            {"drain_intensity": 8},
            {"drain_intensity": 5},
            {"drain_intensity": 9},
            {"drain_intensity": 3},
        ]
        # 2 out of 4
        assert compute_burnout_risk(logs) == 0.5


# ── compute_consistency_score ────────────────────────────────────────

class TestComputeConsistencyScore:
    def test_empty(self):
        assert compute_consistency_score([]) == 0.0

    def test_all_zeros(self):
        assert compute_consistency_score([0] * 30) == 0.0

    def test_perfectly_consistent(self):
        # Same count every day → std_dev = 0 → score = 1
        assert compute_consistency_score([3] * 30) == 1.0

    def test_mixed(self):
        counts = [2, 2, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 0, 0, 2, 2]
        result = compute_consistency_score(counts)
        assert 0.0 <= result <= 1.0


# ── compute_streak_days ──────────────────────────────────────────────

class TestComputeStreakDays:
    def test_empty(self):
        assert compute_streak_days([], date.today()) == 0

    def test_no_today(self):
        assert compute_streak_days([date.today() - timedelta(days=1)], date.today()) == 0

    def test_today_only(self):
        today = date(2026, 3, 10)
        assert compute_streak_days([today], today) == 1

    def test_consecutive_days(self):
        today = date(2026, 3, 10)
        dates = [today, today - timedelta(days=1), today - timedelta(days=2)]
        assert compute_streak_days(dates, today) == 3

    def test_gap_breaks_streak(self):
        today = date(2026, 3, 10)
        dates = [today, today - timedelta(days=1), today - timedelta(days=3)]
        assert compute_streak_days(dates, today) == 2


# ── compute_daily_burnout_score ──────────────────────────────────────

class TestComputeDailyBurnoutScore:
    def test_empty_everything(self):
        score = compute_daily_burnout_score([], {}, {}, [[], [], [], [], []], 4.0)
        assert score == 0.0

    def test_projected_load_only(self):
        tasks = [
            {"scheduled_start_hour": 9, "estimated_duration_mins": 60, "course_id": 1},
        ]
        course_mem = {"1": {"drain_rate": 5}}
        time_stats = {"morning": {"productivity_score": 0.5}}
        score = compute_daily_burnout_score(tasks, course_mem, time_stats, [[], [], [], [], []], 4.0)
        assert 0.0 < score < 1.0

    def test_fatigue_only(self):
        recent = [
            [{"drain_intensity": 9}],  # yesterday
            [{"drain_intensity": 8}],  # 2 days ago
            [],
            [],
            [],
        ]
        score = compute_daily_burnout_score([], {}, {}, recent, 4.0)
        assert 0.0 < score < 1.0

    def test_max_daily_load_zero(self):
        tasks = [
            {"scheduled_start_hour": 14, "estimated_duration_mins": 120, "course_id": 2},
        ]
        course_mem = {"2": {"drain_rate": 8}}
        time_stats = {"afternoon": {"productivity_score": 0.3}}
        score = compute_daily_burnout_score(tasks, course_mem, time_stats, [[], [], [], [], []], 0)
        # projected_load_normalized should be 0 when max_daily_load is 0
        assert 0.0 <= score <= 1.0
