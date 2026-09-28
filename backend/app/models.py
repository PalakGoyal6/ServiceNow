import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from backend.app.db import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'student' | 'staff' | 'admin'
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    department = relationship("Department", back_populates="staff_members")
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    authored_messages = relationship("Message", back_populates="author")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    roll_no = Column(String(50), nullable=False, unique=True)
    programme = Column(String(100), nullable=False)
    year_of_study = Column(Integer, nullable=False)

    user = relationship("User", back_populates="student_profile")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    staff_members = relationship("User", back_populates="department")
    tasks = relationship("Task", back_populates="department")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    urgency = Column(Integer, default=1, nullable=False)  # 1 to 4
    deadline = Column(Date, nullable=True)
    status = Column(String(50), default="open", nullable=False)  # 'open' | 'resolved'
    classification_source = Column(String(50), default="fallback", nullable=False)  # 'llm' | 'fallback'
    classification_raw = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    student = relationship("User", foreign_keys=[student_id])
    tasks = relationship("Task", back_populates="issue", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="issue", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="issue", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    status = Column(
        String(50), default="pending", nullable=False
    )  # 'blocked' | 'pending' | 'in_progress' | 'waiting_on_student' | 'resolved' | 'rejected'
    dept_summary = Column(Text, nullable=False)
    action_needed = Column(Text, nullable=False)
    base_priority = Column(Integer, default=20, nullable=False)
    effective_priority = Column(Integer, default=20, nullable=False)
    assigned_to = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    unblocked_at = Column(DateTime, nullable=True)

    issue = relationship("Issue", back_populates="tasks")
    department = relationship("Department", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assigned_to])

    # Outgoing dependencies (tasks that block this task)
    blocker_links = relationship(
        "TaskDependency",
        foreign_keys="[TaskDependency.task_id]",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    # Incoming dependencies (tasks that this task blocks)
    dependent_links = relationship(
        "TaskDependency",
        foreign_keys="[TaskDependency.blocked_by_task_id]",
        back_populates="blocked_by_task",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("issue_id", "department_id", name="uq_issue_department"),
        Index("ix_tasks_dept_status", "department_id", "status"),
        Index("ix_tasks_issue_id", "issue_id"),
    )


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    blocked_by_task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    reason = Column(Text, nullable=False, default="")
    created_by = Column(String(50), nullable=False, default="ai")  # 'ai' | user_id

    task = relationship("Task", foreign_keys=[task_id], back_populates="blocker_links")
    blocked_by_task = relationship("Task", foreign_keys=[blocked_by_task_id], back_populates="dependent_links")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    author_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    body = Column(Text, nullable=False)
    visibility = Column(String(50), default="student_and_staff", nullable=False)  # 'student_and_staff' | 'department_only'
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    issue = relationship("Issue", back_populates="messages")
    task = relationship("Task")
    author = relationship("User", back_populates="authored_messages")

    __table_args__ = (
        Index("ix_messages_issue_created", "issue_id", "created_at"),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type = Column(String(100), nullable=False)
    payload = Column(Text, nullable=True)  # JSON text
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    issue = relationship("Issue", back_populates="events")
    task = relationship("Task")
    actor = relationship("User")

    __table_args__ = (
        Index("ix_events_issue_created", "issue_id", "created_at"),
    )
