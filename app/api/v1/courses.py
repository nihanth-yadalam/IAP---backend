"""
Course endpoints — from System A.
M13: GET    /courses/
M14: POST   /courses/
M15: PATCH  /courses/{id}
M16: DELETE /courses/{id}
"""

from typing import Any, Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.task import Course
from app.schemas.courses import CourseCreate, CourseUpdate, CourseResponse

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
