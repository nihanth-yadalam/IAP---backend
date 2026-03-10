"""
Reflexion Agent — analyzes task completion patterns and updates user memory.

Called as a background task after every task completion, and periodically via scheduler.
"""

from __future__ import annotations
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta, date
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session
from app.models.user import UserProfile
from app.models.task import Task, TaskLog, ReflexionLog
from app.services.memory_calculator import (
    get_time_block,
    compute_productivity_score,
    compute_weighted_average,
    compute_procrastination_index,
    compute_burnout_risk,
    compute_consistency_score,
    compute_streak_days,
)

logger = logging.getLogger(__name__)


# ── Trigger Checker ──────────────────────────────────────────────────


async def check_reflexion_triggers(user_id: int) -> None:
    """
    Called as a BackgroundTask after every task completion.
    Opens its own DB session since the request session may be closed.
    """
    async with async_session() as db:
        try:
            # Get last_reflexion_at
            profile = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile.scalars().first()
            if not profile:
                return

            last_reflexion = profile.last_reflexion_at

            # Get new logs since last reflexion
            query = select(TaskLog).where(TaskLog.user_id == user_id)
            if last_reflexion:
                query = query.where(TaskLog.completion_time > last_reflexion)
            query = query.order_by(TaskLog.completion_time.asc())

            result = await db.execute(query)
            new_logs = result.scalars().all()

            if not new_logs:
                return

            trigger = None

            # Check triggers in priority order

            # 1. log_count: 10 or more new logs
            if len(new_logs) >= 10:
                trigger = "log_count"

            # 2. extreme_drain: any single log with drain_intensity >= 9
            if not trigger:
                for log in new_logs:
                    if log.drain_intensity >= 9:
                        trigger = "extreme_drain"
                        break

            # 3. drain_spike: 3+ consecutive logs for same course with duration_ratio >= 1.5
            if not trigger:
                # Group logs by course (maintaining order)
                course_sequences: dict[int, list] = defaultdict(list)
                for log in new_logs:
                    # Need task's course_id
                    task = await db.get(Task, log.task_id)
                    if task and task.course_id:
                        course_sequences[task.course_id].append(log)

                for course_id, logs in course_sequences.items():
                    consecutive = 0
                    for log in logs:
                        if log.duration_ratio >= 1.5:
                            consecutive += 1
                            if consecutive >= 3:
                                trigger = "drain_spike"
                                break
                        else:
                            consecutive = 0
                    if trigger:
                        break

            if trigger:
                await run_reflexion_agent(user_id, db, trigger=trigger)

        except Exception as e:
            logger.error(f"[reflexion] Trigger check failed for user {user_id}: {e}")


# ── Main Reflexion Agent ─────────────────────────────────────────────


async def run_reflexion_agent(
    user_id: int,
    db: AsyncSession,
    trigger: str = "scheduled",
) -> None:
    """
    Full reflexion cycle — 8 steps.
    Updates course memory, global stats, behavioral signals, persona, and generates summary.
    """
    try:
        # ── Step 1: Guard clause ──
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalars().first()
        if not profile:
            logger.warning(f"[reflexion] No profile for user {user_id}")
            return

        last_reflexion = profile.last_reflexion_at

        # Count logs since last reflexion
        count_query = select(func.count(TaskLog.id)).where(
            TaskLog.user_id == user_id
        )
        if last_reflexion:
            count_query = count_query.where(TaskLog.completion_time > last_reflexion)
        count_result = await db.execute(count_query)
        log_count = count_result.scalar()

        if log_count < 5:
            logger.info(f"[reflexion] Insufficient data for user {user_id} ({log_count} logs)")
            return

        # ── Step 2: Pull new logs (joined with task data) ──
        query = (
            select(TaskLog, Task)
            .join(Task, TaskLog.task_id == Task.id)
            .where(TaskLog.user_id == user_id)
        )
        if last_reflexion:
            query = query.where(TaskLog.completion_time > last_reflexion)
        query = query.order_by(TaskLog.completion_time.asc())

        result = await db.execute(query)
        rows = result.all()

        new_logs = [(log, task) for log, task in rows]

        # Load current memory
        memory = dict(profile.onboarding_data) if profile.onboarding_data else {}
        subject_modifiers = memory.get("subject_modifiers", {})
        time_block_stats = memory.get("time_block_stats", {})
        behavioral_signals = memory.get("behavioral_signals", {})
        global_settings = memory.get("global_settings", {})

        # Track what changed for the summary
        changes_delta = {}

        # ── Step 3: Update course memory per (course × time_block) ──
        course_block_groups: dict[tuple, list] = defaultdict(list)
        course_all_logs: dict[int, list] = defaultdict(list)

        for log, task in new_logs:
            if task.course_id:
                course_block_groups[(task.course_id, log.time_block)].append(log)
                course_all_logs[task.course_id].append(log)

        for (course_id, block), logs in course_block_groups.items():
            if len(logs) < 2:
                continue

            course_key = str(course_id)
            course_mem = subject_modifiers.get(course_key, {})
            tba = course_mem.get("time_block_affinity", {})
            block_data = tba.get(block, {
                "duration_ratio": 1.0, "avg_drain": 0.5, "completion_rate": 0.5, "sample_count": 0
            })

            # Calculate new observations
            new_duration_ratio = sum(l.duration_ratio for l in logs) / len(logs)
            new_avg_drain = sum(l.drain_intensity / 10 for l in logs) / len(logs)
            new_completion_rate = sum(1 for l in logs if l.was_on_time) / len(logs)
            new_sample_count = len(logs)

            # Blend
            old_dr = block_data.get("duration_ratio", 1.0)
            old_ad = block_data.get("avg_drain", 0.5)
            old_cr = block_data.get("completion_rate", 0.5)

            block_data["duration_ratio"] = compute_weighted_average(old_dr, new_duration_ratio, new_sample_count)
            block_data["avg_drain"] = compute_weighted_average(old_ad, new_avg_drain, new_sample_count)
            block_data["completion_rate"] = compute_weighted_average(old_cr, new_completion_rate, new_sample_count)
            block_data["sample_count"] = block_data.get("sample_count", 0) + new_sample_count

            # Recalculate productivity for this block
            block_data["productivity_score"] = compute_productivity_score(
                block_data["completion_rate"],
                block_data["avg_drain"],
                block_data["duration_ratio"],
            )

            # Write back
            if block not in tba:
                tba[block] = {}
            tba[block] = block_data
            course_mem["time_block_affinity"] = tba
            subject_modifiers[course_key] = course_mem

        # Update top-level course fields
        for course_id, logs in course_all_logs.items():
            course_key = str(course_id)
            course_mem = subject_modifiers.get(course_key, {})
            tba = course_mem.get("time_block_affinity", {})

            # duration_multiplier = weighted average of all block duration_ratios by sample_count
            total_weighted = 0.0
            total_samples = 0
            for bk, bd in tba.items():
                sc = bd.get("sample_count", 0)
                if sc > 0:
                    total_weighted += bd.get("duration_ratio", 1.0) * sc
                    total_samples += sc
            if total_samples > 0:
                course_mem["duration_multiplier"] = total_weighted / total_samples

            # session_count
            course_mem["session_count"] = course_mem.get("session_count", 0) + len(logs)

            # early_finish_rate
            new_early = sum(1 for l in logs if l.duration_ratio < 0.9) / len(logs)
            old_efr = course_mem.get("early_finish_rate", 0.0)
            course_mem["early_finish_rate"] = compute_weighted_average(old_efr, new_early, len(logs))

            subject_modifiers[course_key] = course_mem

        # ── Step 4: Update global time_block_stats ──
        block_groups: dict[str, list] = defaultdict(list)
        for log, task in new_logs:
            block_groups[log.time_block].append(log)

        for block, logs in block_groups.items():
            if len(logs) < 2:
                continue

            block_data = time_block_stats.get(block, {
                "productivity_score": 0.5, "avg_drain": 0.5, "completion_rate": 0.5, "sample_count": 0
            })

            new_avg_drain = sum(l.drain_intensity / 10 for l in logs) / len(logs)
            new_completion_rate = sum(1 for l in logs if l.was_on_time) / len(logs)
            new_sample_count = len(logs)

            old_ad = block_data.get("avg_drain", 0.5)
            old_cr = block_data.get("completion_rate", 0.5)

            block_data["avg_drain"] = compute_weighted_average(old_ad, new_avg_drain, new_sample_count)
            block_data["completion_rate"] = compute_weighted_average(old_cr, new_completion_rate, new_sample_count)
            block_data["sample_count"] = block_data.get("sample_count", 0) + new_sample_count

            # Also blend duration_ratio globally
            new_duration_ratio = sum(l.duration_ratio for l in logs) / len(logs)
            old_dr = block_data.get("duration_ratio", 1.0)
            block_data["duration_ratio"] = compute_weighted_average(old_dr, new_duration_ratio, new_sample_count)

            block_data["productivity_score"] = compute_productivity_score(
                block_data["completion_rate"],
                block_data["avg_drain"],
                block_data.get("duration_ratio", 1.0),
            )

            time_block_stats[block] = block_data

        # ── Step 5: Recalculate behavioral signals ──
        today = datetime.now(timezone.utc).date()
        thirty_days_ago = today - timedelta(days=30)
        seven_days_ago = today - timedelta(days=7)

        # Pull last 30 days of all logs
        all_logs_30d_result = await db.execute(
            select(TaskLog, Task)
            .join(Task, TaskLog.task_id == Task.id)
            .where(
                TaskLog.user_id == user_id,
                func.date(TaskLog.completion_time) >= thirty_days_ago,
            )
        )
        all_logs_30d = all_logs_30d_result.all()

        logs_7d = [
            log for log, task in all_logs_30d
            if log.completion_time.date() >= seven_days_ago
        ]

        # Procrastination index
        preferred_session = global_settings.get("preferred_session_duration_mins", 50)
        proc_data = []
        for log, task in all_logs_30d:
            scheduled_ts = task.scheduled_start_time.timestamp() if task.scheduled_start_time else None
            proc_data.append({
                "completion_time_ts": log.completion_time.timestamp(),
                "scheduled_start_ts": scheduled_ts,
                "actual_duration_mins": log.actual_duration_mins,
            })

        old_proc = behavioral_signals.get("procrastination_index", 0.0)
        new_proc = compute_procrastination_index(proc_data, preferred_session)
        behavioral_signals["procrastination_index"] = new_proc
        if abs(new_proc - old_proc) > 0.1:
            changes_delta["procrastination_index"] = {"old": round(old_proc, 2), "new": round(new_proc, 2)}

        # Burnout risk
        burnout_data = [{"drain_intensity": l.drain_intensity} for l in logs_7d]
        old_burnout = behavioral_signals.get("burnout_risk_score", 0.0)
        new_burnout = compute_burnout_risk(burnout_data)
        behavioral_signals["burnout_risk_score"] = new_burnout
        if abs(new_burnout - old_burnout) > 0.1:
            changes_delta["burnout_risk_score"] = {"old": round(old_burnout, 2), "new": round(new_burnout, 2)}

        # Consistency score
        daily_counts = []
        for i in range(30):
            day = today - timedelta(days=i)
            count = sum(1 for log, task in all_logs_30d if log.completion_time.date() == day)
            daily_counts.append(count)

        old_consistency = behavioral_signals.get("consistency_score", 0.5)
        new_consistency = compute_consistency_score(daily_counts)
        behavioral_signals["consistency_score"] = new_consistency
        if abs(new_consistency - old_consistency) > 0.1:
            changes_delta["consistency_score"] = {"old": round(old_consistency, 2), "new": round(new_consistency, 2)}

        # Streak days
        log_dates = list(set(log.completion_time.date() for log, task in all_logs_30d))
        old_streak = behavioral_signals.get("streak_days", 0)
        new_streak = compute_streak_days(log_dates, today)
        behavioral_signals["streak_days"] = new_streak
        if new_streak != old_streak:
            changes_delta["streak_days"] = {"old": old_streak, "new": new_streak}

        # ── Step 6: Persona assignment ──
        # Find peak block
        peak_block = "morning"
        peak_score = 0.0
        for block_name in ["morning", "afternoon", "evening", "night"]:
            bs = time_block_stats.get(block_name, {})
            ps = bs.get("productivity_score", 0.5)
            if ps > peak_score:
                peak_score = ps
                peak_block = block_name

        morning_score = time_block_stats.get("morning", {}).get("productivity_score", 0.5)
        evening_score = time_block_stats.get("evening", {}).get("productivity_score", 0.5)

        # Global completion rate
        total_logs_all = sum(
            b.get("sample_count", 0) for b in time_block_stats.values()
            if isinstance(b, dict)
        )
        total_on_time_all = sum(
            b.get("completion_rate", 0.5) * b.get("sample_count", 0)
            for b in time_block_stats.values()
            if isinstance(b, dict)
        )
        global_completion_rate = total_on_time_all / total_logs_all if total_logs_all > 0 else 0.5

        # Total session count across all courses
        total_sessions = sum(
            sm.get("session_count", 0)
            for sm in subject_modifiers.values()
            if isinstance(sm, dict)
        )

        persona = "Unclassified"
        confidence = 0.0

        burnout_risk = behavioral_signals.get("burnout_risk_score", 0.0)
        proc_index = behavioral_signals.get("procrastination_index", 0.0)
        consistency = behavioral_signals.get("consistency_score", 0.5)

        # Rules in priority order
        if peak_block in ["evening", "night"] and morning_score < 0.55:
            persona = "The Night Owl"
            confidence = (peak_score - morning_score) / peak_score if peak_score > 0 else 0.0
        elif peak_block == "morning" and evening_score < 0.60:
            persona = "The Early Bird"
            confidence = (morning_score - evening_score) / morning_score if morning_score > 0 else 0.0
        elif proc_index > 0.6:
            persona = "The Procrastinator"
            confidence = proc_index
        elif consistency > 0.75 and global_completion_rate > 0.80 and total_sessions >= 20:
            persona = "The Dedicated Star"
            confidence = (consistency + global_completion_rate) / 2
        else:
            persona = "Unclassified"
            confidence = 0.0

        # ── Step 7: Generate human-readable summary ──
        summary_text = "Your study insights are being calculated."
        try:
            summary_text = await _generate_summary(
                changes_delta=changes_delta,
                persona=persona,
                confidence=confidence,
                burnout_risk=burnout_risk,
                streak=behavioral_signals.get("streak_days", 0),
            )
        except Exception as e:
            logger.error(f"[reflexion] Summary generation failed for user {user_id}: {e}")

        # ── Step 8: Persist in a single transaction ──
        # Build updated memory
        memory["subject_modifiers"] = subject_modifiers
        memory["time_block_stats"] = time_block_stats
        memory["behavioral_signals"] = behavioral_signals

        now_utc = datetime.now(timezone.utc)

        # 1. Patch memory JSONB using merge operator
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

        # 2. Update persona and persona_confidence
        if confidence > 0.5:
            await db.execute(
                text(
                    """
                    UPDATE user_profiles
                    SET current_archetype = :persona,
                        persona_confidence = :confidence,
                        last_reflexion_at = :now
                    WHERE user_id = :user_id
                    """
                ),
                {
                    "user_id": user_id,
                    "persona": persona,
                    "confidence": confidence,
                    "now": now_utc,
                },
            )
        else:
            await db.execute(
                text(
                    """
                    UPDATE user_profiles
                    SET persona_confidence = :confidence,
                        last_reflexion_at = :now
                    WHERE user_id = :user_id
                    """
                ),
                {
                    "user_id": user_id,
                    "confidence": confidence,
                    "now": now_utc,
                },
            )

        # 4. Insert reflexion log
        reflexion_log = ReflexionLog(
            user_id=user_id,
            generated_at=now_utc,
            summary_text=summary_text,
            updated_traits=changes_delta if changes_delta else None,
            reflexion_trigger=trigger,
        )
        db.add(reflexion_log)

        await db.commit()
        logger.info(f"[reflexion] Completed for user {user_id} (trigger={trigger}, persona={persona})")

    except Exception as e:
        await db.rollback()
        logger.error(f"[reflexion] Failed for user {user_id}: {e}")
        raise


# ── Summary Generation ───────────────────────────────────────────────


async def _generate_summary(
    changes_delta: dict,
    persona: str,
    confidence: float,
    burnout_risk: float,
    streak: int,
) -> str:
    """Generate a 3-sentence summary using Gemini. Falls back to default on failure."""
    if not changes_delta:
        return f"Your study pattern is stable. Keep up your {streak}-day streak! Your current persona is {persona}."

    try:
        from app.core.config import settings
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            return _fallback_summary(persona, confidence, burnout_risk, streak)

        from google import genai

        client = genai.Client(api_key=api_key)

        # Build change description
        change_lines = []
        for field, vals in changes_delta.items():
            change_lines.append(f"- {field}: {vals['old']} → {vals['new']}")
        changes_text = "\n".join(change_lines)

        prompt = f"""You are a supportive academic coach writing a short insight summary \
for a student's planner dashboard.

Recent performance changes detected:
{changes_text}

Current persona: {persona} (confidence: {confidence:.0%})
Burnout risk: {burnout_risk:.0%}
Streak: {streak} days

Write exactly 3 sentences. Be encouraging but honest.
Do not use technical terms like 'duration_ratio' or 'sample_count'.
Speak directly to the student as 'you'."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text.strip()

    except Exception as e:
        logger.warning(f"[reflexion] Gemini call failed: {e}")
        return _fallback_summary(persona, confidence, burnout_risk, streak)


def _fallback_summary(persona: str, confidence: float, burnout_risk: float, streak: int) -> str:
    """Static fallback when Gemini is unavailable."""
    parts = []
    if streak > 0:
        parts.append(f"Great job maintaining a {streak}-day study streak!")
    else:
        parts.append("Let's build a consistent study habit together.")

    if burnout_risk > 0.5:
        parts.append("Your recent sessions have been quite draining — consider taking shorter study blocks.")
    else:
        parts.append("Your energy levels look manageable — keep it up!")

    parts.append(f"Your current study persona is {persona}.")
    return " ".join(parts)
