"""
Course endpoints — from System A.
M13: GET    /courses/
M14: POST   /courses/
M15: PATCH  /courses/{id}
M16: DELETE /courses/{id}
"""

from typing import Any, Annotated, List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.task import Course
from app.schemas.courses import CourseCreate, CourseUpdate, CourseResponse
from app.services.memory_utils import add_course_memory

router = APIRouter()


@router.get("/", response_model=List[CourseResponse])
async def read_courses(
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve active courses."""
    query = (
        select(Course)
        .where(Course.user_id == current_user.id, Course.is_archived == False)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=CourseResponse)
async def create_course(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    course_in: CourseCreate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Create new course."""
    course = Course(
        user_id=current_user.id,
        name=course_in.name,
        color_code=course_in.color_code,
        is_archived=course_in.is_archived,
    )
    db.add(course)
    try:
        await db.commit()
        await db.refresh(course)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Course with this name already exists.")

    # Add course entry to AI memory JSONB
    try:
        await add_course_memory(
            db=db,
            user_id=current_user.id,
            course_id=course.id,
            confidence_score=course_in.confidence_score,
            drain_rate=course_in.drain_rate,
        )
        await db.commit()
    except Exception as e:
        print(f"[courses] Failed to add course memory for course {course.id}: {e}")

    return course


@router.patch("/{id}", response_model=CourseResponse)
async def update_course(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    id: int,
    course_in: CourseUpdate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Update a course."""
    result = await db.execute(select(Course).where(Course.id == id, Course.user_id == current_user.id))
    course = result.scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    for field, value in course_in.model_dump(exclude_unset=True).items():
        setattr(course, field, value)

    try:
        db.add(course)
        await db.commit()
        await db.refresh(course)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Course with this name already exists.")
    return course


@router.delete("/{id}")
async def delete_course(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    id: int,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """Delete a course."""
    result = await db.execute(select(Course).where(Course.id == id, Course.user_id == current_user.id))
    course = result.scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    await db.delete(course)
    await db.commit()
    return {"message": "Course deleted successfully"}


# ── M26 — Add manual rule to course memory ───────────────────────────

@router.post("/{course_id}/memory/rules")
async def add_course_memory_rule(
    *,
    db: Annotated[AsyncSession, Depends(deps.get_db)],
    course_id: int,
    current_user: Annotated[User, Depends(deps.get_current_user)],
    rule: str = Body(..., embed=True),
) -> Any:
    """Appends a text rule to the course's manual_rules array inside subject_modifiers."""
    import json
    from sqlalchemy import text

    # Verify course ownership
    result = await db.execute(select(Course).where(Course.id == course_id, Course.user_id == current_user.id))
    course = result.scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course_key = str(course_id)

    await db.execute(
        text(
            """
            UPDATE user_profiles
            SET onboarding_data = jsonb_set(
                COALESCE(onboarding_data, '{}'::jsonb),
                ARRAY['subject_modifiers', :course_key, 'manual_rules'],
                COALESCE(
                    onboarding_data->'subject_modifiers'->:course_key->'manual_rules',
                    '[]'::jsonb
                ) || :rule_json::jsonb,
                true
            )
            WHERE user_id = :user_id
            """
        ),
        {
            "user_id": current_user.id,
            "course_key": course_key,
            "rule_json": json.dumps(rule),
        },
    )
    await db.commit()
    return {"message": "Course rule added successfully", "course_id": course_id, "rule": rule}
