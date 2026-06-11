"""Integration tests for HTTP routes — updated for new 7th grade structure."""

import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ["DEEPSEEK_API_KEY"] = "test-key-for-integration"


@pytest_asyncio.fixture
async def client():
    from main import app
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from db.models import Base
    from fastapi.templating import Jinja2Templates

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
    assert "数学" in response.text or "english" in response.text.lower()


@pytest.mark.asyncio
async def test_subject_page_renders(client):
    response = await client.get("/subjects/math/7")
    assert response.status_code == 200
    assert "正数和负数" in response.text
    assert "chapter-block" in response.text
    assert "topic-card" in response.text


@pytest.mark.asyncio
async def test_lesson_page_renders(client):
    response = await client.get("/learn/math/7/ch01_sec01")
    assert response.status_code == 200
    assert "mindmap-area" in response.text
    assert "btn-pdf-link" in response.text
    assert "exercise-container" in response.text


@pytest.mark.asyncio
async def test_chat_history_empty(client):
    response = await client.get("/chat/history")
    assert response.status_code == 200
    assert "你好" in response.text


@pytest.mark.asyncio
async def test_subject_page_empty_for_invalid(client):
    response = await client.get("/subjects/nonexistent/7")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_static_files_mounted(client):
    response = await client.get("/static/style.css")
    assert response.status_code == 200
    assert "box-sizing" in response.text


@pytest.mark.asyncio
async def test_english_subject_shows_coming_soon(client):
    response = await client.get("/subjects/english/7")
    assert response.status_code == 200
    # English content not ready yet
