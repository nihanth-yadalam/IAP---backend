"""
Task endpoints — from System A (with collision check).
M17: GET    /tasks/
M18: POST   /tasks/
M19: PATCH  /tasks/{id}
M20: DELETE /tasks/{id}
M21: POST   /tasks/{id}/complete
M28: POST   /tasks/estimate-duration
M29: POST   /tasks/recommend-slots
M30: POST   /tasks/confirm-slot
"""

from typing import Any, Annotated, List, Optional
from datetime import datetime, date, time, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.models.task import Task, TaskLog, Course, TaskStatus
from app.models.schedule import FixedSlot
from app.schemas.tasks import TaskCreate, TaskUpdate, TaskResponse, TaskFeedbackRequest, TaskLogResponse
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService
from app.services.sync_engine import SyncEngine
from app.services.memory_calculator import get_time_block
from app.schemas.duration import (
    DurationEstimationRequest, DurationEstimationResponse,
    SlotRecommendationRequest, SlotRecommendationResponse, ConfirmSlotRequest,
)
from app.services.duration_estimator import (
    get_duration_estimation_context,
    build_duration_estimation_prompt,
    call_gemini_for_duration,
)
from app.services.scheduler_service import (
    get_free_slots,
    get_daily_burnout_scores,
    filter_candidate_slots,
    get_scheduling_context,
    build_scheduling_prompt,
    call_gemini_for_scheduling,
)

router = APIRouter()


# ── M28 — AI Duration Estimation ─────────────────────────────────────

@router.post("/estimate-duration", response_model=DurationEstimationResponse)
async def estimate_duration(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    request: DurationEstimationRequest,
) -> Any:
    """AI-powered duration estimation based on student memory. Read-only, no DB writes."""
    # 1. Retrieve memory context
    memory_context = await get_duration_estimation_context(
        user_id=current_user.id,
        course_id=request.course_id,
        db=db,
    )

    # 2. Build the prompt
    task_details = {
        "task_type": request.task_type,
        "difficulty": request.difficulty,
        "description": request.description,
    }
    prompt = build_duration_estimation_prompt(task_details, memory_context)

    # 3. Call Gemini
    result = await call_gemini_for_duration(prompt)

    return result


# ── M29 — AI Slot Recommendation ─────────────────────────────────────

@router.post("/recommend-slots", response_model=SlotRecommendationResponse)
async def recommend_slots(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    request: SlotRecommendationRequest,
) -> Any:
    """AI-powered slot recommendation. Read-only, no DB writes."""
    # 1. Retrieve scheduling context
    memory_context = await get_scheduling_context(
        user_id=current_user.id,
        course_id=request.course_id,
        db=db,
    )

    # 2. Find free slots
    free = await get_free_slots(
        user_id=current_user.id,
        period_start=request.period_start,
        period_end=request.period_end,
        estimated_duration_mins=request.estimated_duration_mins,
        db=db,
    )
    if not free:
        raise HTTPException(
            status_code=404,
            detail="No available slots found in the requested period. Try extending your time window.",
        )

    # 3. Compute daily burnout scores
    burnout_scores = await get_daily_burnout_scores(
        user_id=current_user.id,
        period_start=request.period_start,
        period_end=request.period_end,
        db=db,
    )

    # 4. Pre-filter candidates
    candidates = filter_candidate_slots(
        free_slots=free,
        burnout_scores=burnout_scores,
        course_memory=memory_context["course_memory"],
        user_memory={"time_block_stats": memory_context["time_block_stats"]},
    )
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="No suitable slots found after applying your schedule constraints and burnout levels.",
        )

    # 5. Build prompt
    task_details = {
        "task_type": request.task_type,
        "difficulty": request.difficulty,
        "description": request.description,
    }
    prompt = build_scheduling_prompt(
        task_details=task_details,
        candidate_slots=candidates,
        memory_context=memory_context,
        estimated_duration_mins=request.estimated_duration_mins,
    )

    # 6. Call Gemini
    result = await call_gemini_for_scheduling(
        prompt=prompt,
        estimated_duration_mins=request.estimated_duration_mins,
        period_start=request.period_start,
        period_end=request.period_end,
    )

    return result


# ── M30 — Confirm Slot ───────────────────────────────────────────────

@router.post("/confirm-slot", response_model=TaskResponse)
async def confirm_slot(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    request: ConfirmSlotRequest,
) -> Any:
    """Confirm a recommended or manually-chosen slot for a task."""
    # 1. Verify task exists and belongs to user
    task_result = await db.execute(
        select(Task)
        .options(selectinload(Task.course))
        .where(Task.id == request.task_id, Task.user_id == current_user.id)
    )
    task = task_result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 2. Verify status
    if task.status == TaskStatus.Completed:
        raise HTTPException(
            status_code=400,
            detail="Cannot schedule a completed task.",
        )

    # 3. Check for conflicts
    day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
        request.scheduled_date.weekday()
    ]

    # 3a. Check fixed slots
    fixed_result = await db.execute(
        select(FixedSlot).where(
            FixedSlot.user_id == current_user.id,
            FixedSlot.day_of_week == day_name,
            FixedSlot.is_deleted == False,
        )
    )
    for slot in fixed_result.scalars().all():
        if slot.start_time and slot.end_time:
            if _times_overlap(
                request.scheduled_start_time, request.scheduled_end_time,
                slot.start_time, slot.end_time,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="This slot conflicts with an existing commitment. Please choose another time.",
                )

    # 3b. Check scheduled tasks
    day_start_dt = datetime.combine(request.scheduled_date, time(0, 0), tzinfo=timezone.utc)
    day_end_dt = datetime.combine(request.scheduled_date + timedelta(days=1), time(0, 0), tzinfo=timezone.utc)

    task_clash_result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.id != request.task_id,
            Task.scheduled_start_time >= day_start_dt,
            Task.scheduled_start_time < day_end_dt,
            Task.status != TaskStatus.Completed,
        )
    )
    for existing_task in task_clash_result.scalars().all():
        if existing_task.scheduled_start_time and existing_task.scheduled_end_time:
            if _times_overlap(
                request.scheduled_start_time, request.scheduled_end_time,
                existing_task.scheduled_start_time.time(), existing_task.scheduled_end_time.time(),
            ):
                raise HTTPException(
                    status_code=409,
                    detail="This slot conflicts with an existing commitment. Please choose another time.",
                )

    # 4. Write scheduled times
    from datetime import datetime
    import tzlocal
    
    local_tz = tzlocal.get_localzone()

    task.course_id = request.course_id
    task.scheduled_start_time = datetime.combine(
        request.scheduled_date, request.scheduled_start_time
    ).replace(tzinfo=local_tz)
    
    task.scheduled_end_time = datetime.combine(
        request.scheduled_date, request.scheduled_end_time
    ).replace(tzinfo=local_tz)
    
    task.status = TaskStatus.In_Progress

    await db.commit()
    await db.refresh(task)

    # 5. Push to Google Calendar if linked
    await _push_task_to_google(db, current_user, task)

    return task


def _times_overlap(s1: time, e1: time, s2: time, e2: time) -> bool:
    """Check if two time ranges overlap."""
    return s1 < e2 and s2 < e1


def _calendar_service() -> CalendarService:
    return CalendarService(GoogleOAuthService())


def _build_sync_engine() -> SyncEngine:
    oauth = GoogleOAuthService()
    cal = CalendarService(oauth)
    return SyncEngine(oauth, cal)


async def _push_task_to_google(db: AsyncSession, user: User, task: Task):
    """Create or update a Google Calendar event for a task."""
    if not user.google_refresh_token:
        return
    if not task.scheduled_start_time or not task.scheduled_end_time:
        return

    cal = _calendar_service()
    slot_data = {
        "title": task.title,
        "google_start_datetime": task.scheduled_start_time,
        "google_end_datetime": task.scheduled_end_time,
    }

    try:
        if task.google_event_id:
            cal.update_event(user.google_refresh_token, "primary", task.google_event_id, slot_data)
        else:
            event_id = cal.create_event(user.google_refresh_token, "primary", slot_data)
            task.google_event_id = event_id
            await db.commit()
    except Exception as e:
        print(f"[task-sync] Failed to push task {task.id} to Google: {e}")


async def _delete_task_from_google(user: User, google_event_id: str | None):
    """Delete a Google Calendar event for a task."""
    if not user.google_refresh_token or not google_event_id:
        return
    cal = _calendar_service()
    try:
        cal.delete_event(user.google_refresh_token, "primary", google_event_id)
    except Exception as e:
        print(f"[task-sync] Failed to delete event {google_event_id} from Google: {e}")


# ── Collision checker ─────────────────────────────────────────────────

async def check_collision(
    db: AsyncSession,
    user_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_task_id: Optional[int] = None,
    current_user: Optional[User] = None,
):
    """Raise 409 if a task or fixed-slot collision is detected."""
    if start_time >= end_time:
        return

    # Auto-sync from Google Calendar so un-pulled events are caught
    if current_user and current_user.google_refresh_token:
        try:
            engine = _build_sync_engine()
            await engine.sync_from_google(db, user_id)
        except Exception as e:
            print(f"[collision] Auto-sync failed (continuing with local data): {e}")

    # Task collision: overlap = (StartA < EndB) and (EndA > StartB)
    query = select(Task).where(
        Task.user_id == user_id,
        Task.scheduled_start_time < end_time,
        Task.scheduled_end_time > start_time,
    )
    if exclude_task_id:
        query = query.where(Task.id != exclude_task_id)

    result = await db.execute(query)
    conflict = result.scalars().first()
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Time slot overlaps with existing task: '{conflict.title}' "
                f"({conflict.scheduled_start_time} - {conflict.scheduled_end_time})"
            ),
        )

    # Fixed-slot (recurring) collision — weekly fields
    # Convert UTC task times to user's local timezone before comparing
    # because recurring slots store times in the user's local timezone
    from zoneinfo import ZoneInfo
    user_tz_name = "UTC"  # fallback
    if current_user and current_user.profile and current_user.profile.timezone:
        user_tz_name = current_user.profile.timezone
    try:
        user_tz = ZoneInfo(user_tz_name)
    except Exception:
        user_tz = ZoneInfo("UTC")

    # Convert to user's local timezone
    local_start = start_time.astimezone(user_tz) if start_time.tzinfo else start_time
    local_end = end_time.astimezone(user_tz) if end_time.tzinfo else end_time
    day_name = local_start.strftime("%A")
    t_start = local_start.time().replace(tzinfo=None)
    t_end = local_end.time().replace(tzinfo=None)

    print(f"[collision] User timezone: {user_tz_name}")
    print(f"[collision] Checking recurring slots: task_day={day_name!r} task_start={t_start!r} task_end={t_end!r} (local time)")

    # Debug: show all recurring slots for this user
    all_slots_result = await db.execute(
        select(FixedSlot).where(
            FixedSlot.user_id == user_id,
            FixedSlot.day_of_week.isnot(None),
            FixedSlot.is_deleted == False,
        )
    )
    all_slots = all_slots_result.scalars().all()
    for s in all_slots:
        print(f"[collision]   slot id={s.id} day={s.day_of_week!r} start={s.start_time!r} end={s.end_time!r} title={s.title!r}")

    query = select(FixedSlot).where(
        FixedSlot.user_id == user_id,
        FixedSlot.day_of_week == day_name,
        FixedSlot.start_time < t_end,
        FixedSlot.end_time > t_start,
        FixedSlot.is_deleted == False,
    )
    result = await db.execute(query)
    slot_conflict = result.scalars().first()
    if slot_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Time slot overlaps with fixed schedule: '{slot_conflict.title}' "
                f"({slot_conflict.day_of_week} {slot_conflict.start_time} - {slot_conflict.end_time})"
            ),
        )
    else:
        print(f"[collision] No recurring slot collision found")

    # Fixed-slot (Google Calendar busy slots) — absolute datetime fields
    query = select(FixedSlot).where(
        FixedSlot.user_id == user_id,
        FixedSlot.google_start_datetime < end_time,
        FixedSlot.google_end_datetime > start_time,
        FixedSlot.is_deleted == False,
    )
    result = await db.execute(query)
    google_conflict = result.scalars().first()
    if google_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Time slot overlaps with Google Calendar event: '{google_conflict.title}' "
                f"({google_conflict.google_start_datetime} - {google_conflict.google_end_datetime})"
            ),
        )


# ── M17 — List tasks ─────────────────────────────────────────────────

@router.get("/", response_model=List[TaskResponse])
async def read_tasks(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve tasks. Optionally filter by date range."""
    query = (
        select(Task)
        .options(selectinload(Task.course))
        .where(Task.user_id == current_user.id)
    )

    if start_date and end_date:
        query = query.where(
            or_(
                and_(Task.scheduled_start_time >= start_date, Task.scheduled_start_time <= end_date),
                and_(Task.deadline >= start_date, Task.deadline <= end_date, Task.scheduled_start_time == None),
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ── M18 — Create task ────────────────────────────────────────────────

@router.post("/", response_model=TaskResponse)
async def create_task(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    task_in: TaskCreate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Create a new task."""
    if task_in.course_id:
        course = await db.get(Course, task_in.course_id)
        if not course or course.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Course not found")

    if task_in.scheduled_start_time and task_in.scheduled_end_time:
        await check_collision(db, current_user.id, task_in.scheduled_start_time, task_in.scheduled_end_time, current_user=current_user)

    task = Task(
        user_id=current_user.id,
        course_id=task_in.course_id,
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        category=task_in.category,
        status=task_in.status,
        deadline=task_in.deadline,
        scheduled_start_time=task_in.scheduled_start_time,
        scheduled_end_time=task_in.scheduled_end_time,
        estimated_duration_mins=task_in.estimated_duration_mins,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Push to Google Calendar
    await _push_task_to_google(db, current_user, task)

    if task.course_id:
        stmt = select(Task).options(selectinload(Task.course)).where(Task.id == task.id)
        result = await db.execute(stmt)
        task = result.scalars().first()

    return task


# ── M19 — Update task ────────────────────────────────────────────────

@router.patch("/{id}", response_model=TaskResponse)
async def update_task(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    id: int,
    task_in: TaskUpdate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Update a task."""
    query = (
        select(Task)
        .options(selectinload(Task.course))
        .where(Task.id == id, Task.user_id == current_user.id)
    )
    result = await db.execute(query)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    new_start = task_in.scheduled_start_time if task_in.scheduled_start_time is not None else task.scheduled_start_time
    new_end = task_in.scheduled_end_time if task_in.scheduled_end_time is not None else task.scheduled_end_time

    if new_start and new_end:
        await check_collision(db, current_user.id, new_start, new_end, exclude_task_id=task.id, current_user=current_user)

    for field, value in task_in.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.add(task)
    await db.commit()
    await db.refresh(task)

    # If task is now Completed, delete the Google Calendar event
    if task.status == TaskStatus.Completed and task.google_event_id:
        await _delete_task_from_google(current_user, task.google_event_id)
        task.google_event_id = None
        await db.commit()
    else:
        # Push changes to Google Calendar
        await _push_task_to_google(db, current_user, task)

    return task


# ── M20 — Delete task ────────────────────────────────────────────────

@router.delete("/{id}")
async def delete_task(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    id: int,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Delete a task."""
    result = await db.execute(select(Task).where(Task.id == id, Task.user_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Delete from Google Calendar first
    await _delete_task_from_google(current_user, task.google_event_id)

    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted successfully"}


# ── M21 — Complete task (feedback endpoint) ──────────────────────────

@router.post("/{task_id}/complete", response_model=TaskLogResponse)
async def complete_task(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    task_id: int,
    feedback: TaskFeedbackRequest,
    current_user: Annotated[User, Depends(deps.get_current_user)],
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Mark a task as completed with user feedback.
    Calculates derived fields server-side and triggers reflexion check in background.
    """
    # 1. Verify task exists
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 2. Verify ownership
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to complete this task")

    # 3. Verify not already completed
    if task.status == TaskStatus.Completed:
        raise HTTPException(status_code=400, detail="Task is already completed")

    # 4. Set completion time
    completion_time = datetime.now(timezone.utc)

    # 5. Derive computed fields
    time_block = get_time_block(completion_time.hour)

    if task.deadline:
        was_on_time = completion_time <= task.deadline
        if not was_on_time:
            delay_mins = int((completion_time - task.deadline).total_seconds() / 60)
        else:
            delay_mins = 0
    else:
        was_on_time = True
        delay_mins = 0

    if task.estimated_duration_mins and task.estimated_duration_mins > 0:
        duration_ratio = feedback.actual_duration_mins / task.estimated_duration_mins
    else:
        duration_ratio = 1.0

    # 6. Update task status to Completed
    task.status = TaskStatus.Completed
    db.add(task)

    # 7. Create task log
    task_log = TaskLog(
        task_id=task.id,
        user_id=current_user.id,
        actual_duration_mins=feedback.actual_duration_mins,
        drain_intensity=feedback.drain_intensity,
        mood_note=feedback.mood_note,
        completion_time=completion_time,
        time_block=time_block,
        was_on_time=was_on_time,
        delay_mins=delay_mins,
        duration_ratio=duration_ratio,
        ai_feedback_tags=None,
    )
    db.add(task_log)
    await db.commit()
    await db.refresh(task_log)

    # 8. Delete from Google Calendar if linked
    if task.google_event_id:
        await _delete_task_from_google(current_user, task.google_event_id)
        task.google_event_id = None
        await db.commit()

    # 9. Trigger reflexion check in background (non-blocking)
    from app.services.reflexion_agent import check_reflexion_triggers
    background_tasks.add_task(check_reflexion_triggers, current_user.id)

    return task_log

