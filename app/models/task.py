"""
Course + Task + TaskLog + ReflexionLog models.
"""

from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import (
    Integer, String, Boolean, Float, ForeignKey, DateTime, Text,
    Enum as SQLEnum, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
import enum


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


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color_code: Mapped[str] = mapped_column(String, nullable=False)
    term: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="courses")
    tasks = relationship("Task", back_populates="course", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uix_user_course_name"),
    )


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
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_duration_mins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Future: Intelligent Task Decomposition
    parent_task_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    is_high_burden: Mapped[bool] = mapped_column(Boolean, default=False)

    # Google Calendar sync
    google_event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="tasks")
    course = relationship("Course", back_populates="tasks")
    subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan")
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    task_log: Mapped[Optional["TaskLog"]] = relationship(
        "TaskLog", back_populates="task", uselist=False, cascade="all, delete-orphan"
    )


class TaskLog(Base):
    """Record created when a user marks a task complete — stores feedback and derived metrics."""
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # User feedback fields
    actual_duration_mins: Mapped[int] = mapped_column(Integer, nullable=False)
    drain_intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    mood_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completion_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Derived fields (calculated by backend at write time)
    time_block: Mapped[str] = mapped_column(String(20), nullable=False)
    was_on_time: Mapped[bool] = mapped_column(Boolean, nullable=False)
    delay_mins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    ai_feedback_tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="task_log")
    user = relationship("User", back_populates="task_logs")

    __table_args__ = (
        CheckConstraint("drain_intensity >= 1 AND drain_intensity <= 10", name="ck_drain_intensity_range"),
    )


class ReflexionLog(Base):
    """Historical record of each reflexion agent run."""
    __tablename__ = "reflexion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_traits: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reflexion_trigger: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    user = relationship("User", back_populates="reflexion_logs")
