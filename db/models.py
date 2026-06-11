"""SQLAlchemy ORM models for JimmyCoach."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from db.database import Base


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    topic_id = Column(String(100), nullable=False)
    duration_sec = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    confidence_score = Column(Integer, default=0)  # 1-5, 0=not set

    exercises = relationship("ExerciseAttempt", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=False)
    exercise_id = Column(String(100), nullable=False)
    student_answer = Column(Text, nullable=False, default="")
    is_correct = Column(Boolean, nullable=True)
    ai_feedback = Column(Text, nullable=True)

    session = relationship("StudySession", back_populates="exercises")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("StudySession", back_populates="messages")


class ProgressSnapshot(Base):
    __tablename__ = "progress_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(String(100), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default="not_started")
    last_studied = Column(DateTime, nullable=True)
    attempts_count = Column(Integer, default=0)


class ErrorLog(Base):
    """Track wrong answers for the error book feature."""
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(50), nullable=False, default="math")
    section_id = Column(String(100), nullable=False)
    exercise_idx = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    error_count = Column(Integer, default=1)
    last_error_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PipelineTask(Base):
    """Track PDF processing pipeline tasks."""
    __tablename__ = "pipeline_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(50), nullable=False)
    subject_name = Column(String(50), nullable=False)
    grade = Column(Integer, nullable=False)
    semester = Column(String(10), nullable=False, default="上册")
    pdf_path = Column(String(500), nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    progress = Column(Integer, default=0)
    chapters_json = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
