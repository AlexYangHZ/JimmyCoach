"""Integration tests for HTTP routes."""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient

os.environ["DEEPSEEK_API_KEY"] = "test-key-for-integration"


@pytest_asyncio.fixture
async def client():
    from main import app

    # Mock the database dependency to use in-memory DB
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from db.models import Base

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    from db.database import get_db
    from fastapi.templating import Jinja2Templates
    app.dependency_overrides[get_db] = override_get_db
    app.state.templates = Jinja2Templates(directory="templates")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_home_page_renders(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Jimmy教练" in response.text
    assert "数学" in response.text


@pytest.mark.asyncio
async def test_subject_page_renders(client):
    response = await client.get("/subjects/math/6")
    assert response.status_code == 200
    assert "分数" in response.text
    assert "topic-list" in response.text


@pytest.mark.asyncio
async def test_lesson_page_renders(client):
    response = await client.get("/learn/math/6/fractions-basics")
    assert response.status_code == 200
    assert "chat-panel" in response.text


@pytest.mark.asyncio
async def test_chat_history_empty(client):
    response = await client.get("/chat/history?topic=fractions-basics")
    assert response.status_code == 200
    assert "你好" in response.text


@pytest.mark.asyncio
async def test_subject_page_empty_for_invalid(client):
    response = await client.get("/subjects/nonexistent/6")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_static_files_mounted(client):
    response = await client.get("/static/style.css")
    assert response.status_code == 200
    assert "box-sizing" in response.text


@pytest.mark.asyncio
async def test_free_chat_page(client):
    response = await client.get("/chat")
    assert response.status_code == 200
    assert "自由提问" in response.text
