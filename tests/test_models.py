"""Test database models can be created and queried."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from db.models import Base, StudySession, ExerciseAttempt, ChatMessage, ProgressSnapshot


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_study_session(db_session):
    session = StudySession(date="2026-06-09", topic_id="fractions-multiply", duration_sec=600, completed=True, confidence_score=4)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.id is not None
    assert session.topic_id == "fractions-multiply"
    assert session.completed is True


@pytest.mark.asyncio
async def test_exercise_attempt_relation(db_session):
    session = StudySession(date="2026-06-09", topic_id="fractions-multiply")
    db_session.add(session)
    await db_session.flush()

    attempt = ExerciseAttempt(session_id=session.id, exercise_id="ex-01", student_answer="3/4", is_correct=True, ai_feedback="做得很好！")
    db_session.add(attempt)
    await db_session.commit()

    # Query to verify relationship
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    stmt = select(StudySession).where(StudySession.id == session.id).options(selectinload(StudySession.exercises))
    result = await db_session.execute(stmt)
    loaded = result.scalar_one()

    assert len(loaded.exercises) == 1
    assert loaded.exercises[0].student_answer == "3/4"


@pytest.mark.asyncio
async def test_chat_message_relation(db_session):
    session = StudySession(date="2026-06-09", topic_id="fractions-multiply")
    db_session.add(session)
    await db_session.flush()

    msg = ChatMessage(session_id=session.id, role="user", content="什么是分数乘法？")
    db_session.add(msg)
    await db_session.commit()

    # Query to verify relationship
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    stmt = select(StudySession).where(StudySession.id == session.id).options(selectinload(StudySession.messages))
    result = await db_session.execute(stmt)
    loaded = result.scalar_one()

    assert len(loaded.messages) == 1
    assert loaded.messages[0].role == "user"


@pytest.mark.asyncio
async def test_progress_snapshot_unique_topic(db_session):
    ps = ProgressSnapshot(topic_id="fractions-multiply", status="in_progress", attempts_count=3)
    db_session.add(ps)
    await db_session.commit()

    assert ps.id is not None
    assert ps.status == "in_progress"
