"""
Task endpoints — from System A (with collision check).
M17: GET    /tasks/
M18: POST   /tasks/
M19: PATCH  /tasks/{id}
M20: DELETE /tasks/{id}
"""

from typing import Any, Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.models.task import Task, Course
from app.models.schedule import FixedSlot
from app.schemas.tasks import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()


# ── Collision checker ─────────────────────────────────────────────────

async def check_collision(
    db: AsyncSession,
    user_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_task_id: Optional[int] = None,
):
    """Raise 409 if a task or fixed-slot collision is detected."""
    if start_time >= end_time:
        return

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

    # Fixed-slot (recurring) collision
    day_name = start_time.strftime("%A")
    t_start = start_time.time()
    t_end = end_time.time()

    query = select(FixedSlot).where(
        FixedSlot.user_id == user_id,
        FixedSlot.day_of_week == day_name,
        FixedSlot.start_time < t_end,
        FixedSlot.end_time > t_start,
    )
    result = await db.execute(query)
    slot_conflict = result.scalars().first()
    if slot_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Time slot overlaps with fixed schedule: '{slot_conflict.label}' "
                f"({slot_conflict.start_time} - {slot_conflict.end_time})"
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
        await check_collision(db, current_user.id, task_in.scheduled_start_time, task_in.scheduled_end_time)

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
        await check_collision(db, current_user.id, new_start, new_end, exclude_task_id=task.id)

    for field, value in task_in.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.add(task)
    await db.commit()
    await db.refresh(task)
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

    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted successfully"}
