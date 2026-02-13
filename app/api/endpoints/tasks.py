from typing import Any, Annotated, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.models.task import Task, Course
from app.models.schedule import FixedSlot, DayOfWeek
from app.schemas.tasks import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()

async def check_collision(db: AsyncSession, user_id: int, start_time: datetime, end_time: datetime, exclude_task_id: Optional[int] = None):
    # 1. Check Payload Logic (Sanity) - handled by Pydantic, but good to double check if called internally
    if start_time >= end_time:
         return # Should limit this check/error? Pydantic handles it.

    # 2. Check Task Collisions
    # Overlap: (StartA < EndB) and (EndA > StartB)
    query = select(Task).where(
        Task.user_id == user_id,
        Task.scheduled_start_time < end_time,
        Task.scheduled_end_time > start_time
    )
    if exclude_task_id:
        query = query.where(Task.id != exclude_task_id)
        
    result = await db.execute(query)
    conflicting_task = result.scalars().first()
    if conflicting_task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Time slot overlaps with existing task: '{conflicting_task.title}' ({conflicting_task.scheduled_start_time} - {conflicting_task.scheduled_end_time})"
        )

    # 3. Check Fixed Slot Collisions
    # Need to match Day of Week
    # We assume 'start_time' and 'end_time' are on the same day for a single task slot mostly, 
    # but if it spans midnight, we might need to be careful. For now, assuming single day tasks or checking both days.
    # Simple logic: Check the day of the start_time.
    
    day_name = start_time.strftime("%A") # e.g., 'Monday'
    # Map to Enum just to be safe or use string direct if DB stores string
    
    # DB stores 'Monday' etc.
    
    # Time comparison
    # We need to extract HH:MM from the task's datetime
    task_start_time_time = start_time.time()
    task_end_time_time = end_time.time()
    
    # Query fixed slots for this day
    query = select(FixedSlot).where(
        FixedSlot.user_id == user_id,
        FixedSlot.day_of_week == day_name,
        FixedSlot.start_time < task_end_time_time,
        FixedSlot.end_time > task_start_time_time
    )
    
    result = await db.execute(query)
    conflicting_slot = result.scalars().first()
    if conflicting_slot:
         raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Time slot overlaps with fixed schedule: '{conflicting_slot.label}' ({conflicting_slot.start_time} - {conflicting_slot.end_time})"
        )

@router.get("/", response_model=List[TaskResponse])
async def read_tasks(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve tasks. Filter by date range if provided.
    Logic: Return tasks where scheduled_start_time is within range OR deadline is within range (if not yet scheduled).
    """
    query = select(Task).options(selectinload(Task.course)).where(Task.user_id == current_user.id)
    
    if start_date and end_date:
        # Complex filter: 
        # (Scheduled Start between Range) OR (Deadline between Range AND Scheduled Start IS NULL)
        # Actually prompt says: "Return tasks where scheduled_start_time is within range OR deadline is within range (if not yet scheduled)"
        # Let's interpret strict logic:
        # Condition A: scheduled_start_time >= start_date AND scheduled_start_time <= end_date
        # Condition B: deadline >= start_date AND deadline <= end_date AND scheduled_start_time IS NULL
        
        query = query.where(
            or_(
                and_(Task.scheduled_start_time >= start_date, Task.scheduled_start_time <= end_date),
                and_(Task.deadline >= start_date, Task.deadline <= end_date, Task.scheduled_start_time == None)
            )
        )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=TaskResponse)
async def create_task(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    task_in: TaskCreate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Create a new task.
    """
    # Verify Course if provided
    if task_in.course_id:
        course = await db.get(Course, task_in.course_id)
        if not course or course.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Course not found")

    # Collision Warning
    if task_in.scheduled_start_time and task_in.scheduled_end_time:
        await check_collision(db, current_user.id, task_in.scheduled_start_time, task_in.scheduled_end_time)

    # Create Task
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
        estimated_duration_mins=task_in.estimated_duration_mins
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Eager load course for response
    # Or rely on lazy loading if configured, but async requires care.
    # We can re-fetch with options or just return. TaskResponse has Optional[CourseInTask].
    # If we want to return the course details immediately, we should load it.
    if task.course_id:
        stmt = select(Task).options(selectinload(Task.course)).where(Task.id == task.id)
        result = await db.execute(stmt)
        task = result.scalars().first()

    return task

@router.patch("/{id}", response_model=TaskResponse)
async def update_task(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    id: int,
    task_in: TaskUpdate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Update a task.
    """
    query = select(Task).options(selectinload(Task.course)).where(Task.id == id, Task.user_id == current_user.id)
    result = await db.execute(query)
    task = result.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Collision Check if times are changing
    # We need to construct the *new* effective start/end times to check collision
    new_start = task_in.scheduled_start_time if task_in.scheduled_start_time is not None else task.scheduled_start_time
    new_end = task_in.scheduled_end_time if task_in.scheduled_end_time is not None else task.scheduled_end_time
    
    # Only check if we have a valid slot (both exist limits) AND (times are changing from DB or we just want to re-validate integrity)
    # If user updates only title, new_start/new_end are same as old. Collision check will exclude own task_id so it won't self-collide.
    # But it might be expensive to check every time.
    # Let's check if times are actually being modified or if they exist.
    
    # If the resulting state has both times:
    if new_start and new_end:
        # Check collision, excluding self
        await check_collision(db, current_user.id, new_start, new_end, exclude_task_id=task.id)

    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/{id}", response_model=Any)
async def delete_task(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    id: int,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Delete a task.
    """
    result = await db.execute(select(Task).where(Task.id == id, Task.user_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted successfully"}
