"""
Course + Task models — from System A (unchanged).
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, String, Boolean, ForeignKey, DateTime, Text,
    Enum as SQLEnum, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


# ── Enums ────────────────────────────────────────────────────────────

class PriorityLevel(str, enum.Enum):
    High = "High"
    Medium = "Medium"
    Low = "Low"


class TaskCategory(str, enum.Enum):
    Assignment = "Assignment"
    Exam = "Exam"
    Project = "Project"
    Study = "Study"


class TaskStatus(str, enum.Enum):
    Pending = "Pending"
    In_Progress = "In_Progress"
    Completed = "Completed"


# ── Course ───────────────────────────────────────────────────────────

class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    color_code: Mapped[str] = mapped_column(String, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="courses")
    tasks = relationship("Task", back_populates="course", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uix_user_course_name"),
    )


# ── Task ─────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    priority: Mapped[PriorityLevel] = mapped_column(
        SQLEnum(PriorityLevel), default=PriorityLevel.Medium, nullable=False
    )
    category: Mapped[TaskCategory] = mapped_column(
        SQLEnum(TaskCategory), default=TaskCategory.Study, nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus), default=TaskStatus.Pending, nullable=False
    )

    # Time columns
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    estimated_duration_mins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Future: Intelligent Task Decomposition
    parent_task_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    is_high_burden: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="tasks")
    course = relationship("Course", back_populates="tasks")
    subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan")
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
