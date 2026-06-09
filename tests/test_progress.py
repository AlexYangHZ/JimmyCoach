"""Test progress service."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from db.models import Base
from services.progress import ProgressService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_start_and_complete_session(db_session):
    svc = ProgressService(db_session)

    session_id = await svc.start_session("fractions-basics")
    assert session_id > 0

    await svc.complete_session(session_id, confidence_score=4, duration_sec=300)

    from db.models import StudySession
    session = await db_session.get(StudySession, session_id)
    assert session.completed is True
    assert session.confidence_score == 4


@pytest.mark.asyncio
async def test_add_exercise_and_chat(db_session):
    svc = ProgressService(db_session)

    session_id = await svc.start_session("fractions-basics")

    await svc.add_exercise_attempt(session_id, "ex-01", "3/4", True, "做得好！")
    await svc.add_chat_message(session_id, "user", "为什么？")
    await svc.add_chat_message(session_id, "assistant", "因为...")

    history = await svc.get_chat_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"


@pytest.mark.asyncio
async def test_get_progress_summary(db_session):
    svc = ProgressService(db_session)

    await svc.start_session("fractions-basics")

    topics = [
        {"id": "fractions-basics", "title": "分数的基本性质", "order": 1, "dependencies": [], "key_points": []},
        {"id": "fractions-multiply", "title": "分数乘法", "order": 2, "dependencies": ["fractions-basics"], "key_points": []},
    ]

    enriched = await svc.get_progress_summary(topics)
    assert enriched[0]["status"] == "in_progress"
    assert enriched[1]["status"] == "not_started"


@pytest.mark.asyncio
async def test_progress_snapshot_upsert(db_session):
    svc = ProgressService(db_session)

    sid1 = await svc.start_session("fractions-basics")
    await svc.complete_session(sid1, 3, 200)

    sid2 = await svc.start_session("fractions-basics")

    topics = [{"id": "fractions-basics", "title": "...", "order": 1, "dependencies": [], "key_points": []}]
    enriched = await svc.get_progress_summary(topics)
    assert enriched[0]["attempts_count"] == 2
