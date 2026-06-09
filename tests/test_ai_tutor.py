"""Test AI tutor service — prompt building and API call structure."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from services.ai_tutor import AITutorService


@pytest.fixture
def prompts_dir():
    return Path(__file__).parent.parent / "prompts"


@pytest.fixture
def ai_tutor(prompts_dir):
    return AITutorService(
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        prompts_dir=prompts_dir,
    )


def test_build_teach_messages(ai_tutor):
    topic_meta = {
        "topic_id": "fractions-basics",
        "difficulty_level": 1,
        "teaching_approach": "用生活中的分物品例子引入",
        "common_mistakes": ["混淆分子和分母"],
    }

    messages = ai_tutor.build_teach_messages(topic_meta)

    assert len(messages) >= 2
    assert messages[0]["role"] == "system"
    assert "小教练" in messages[0]["content"]
    assert "fractions-basics" in messages[-1]["content"]


def test_build_grade_messages(ai_tutor):
    exercise = {
        "id": "ex-01",
        "question": "1/2 + 1/2 = ?",
        "correct": "1",
        "type": "fill_blank",
    }

    messages = ai_tutor.build_grade_messages(
        exercise=exercise,
        student_answer="2/2",
        topic_context="分数加法"
    )

    assert messages[0]["role"] == "system"
    assert "1/2 + 1/2" in messages[-1]["content"]
    assert "2/2" in messages[-1]["content"]


def test_build_chat_messages(ai_tutor):
    history = [
        {"role": "user", "content": "什么是分数？"},
        {"role": "assistant", "content": "分数就像分披萨..."},
    ]

    messages = ai_tutor.build_chat_messages(
        user_message="我不太明白",
        chat_history=history,
        topic_context={"topic_id": "fractions-basics", "title": "分数的基本性质"},
    )

    assert messages[0]["role"] == "system"
    assert "分数的基本性质" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "我不太明白"


@pytest.mark.asyncio
async def test_grade_answer_correct(ai_tutor):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="对错: 正确\n反馈: 做得很好！答案完全正确。"))
    ]

    async def mock_create(*args, **kwargs):
        return mock_response

    with patch.object(ai_tutor.client.chat.completions, "create", new=mock_create):
        result = await ai_tutor.grade_answer(
            exercise={"question": "1+1=?", "correct": "2"},
            student_answer="2",
            topic_context="加法",
        )

    assert result["is_correct"] is True
    assert "做得很好" in result["feedback"]


@pytest.mark.asyncio
async def test_grade_answer_incorrect(ai_tutor):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="对错: 错误\n反馈: 再想想，分母不能直接相加哦。"))
    ]

    async def mock_create(*args, **kwargs):
        return mock_response

    with patch.object(ai_tutor.client.chat.completions, "create", new=mock_create):
        result = await ai_tutor.grade_answer(
            exercise={"question": "1/2+1/3=?", "correct": "5/6"},
            student_answer="2/5",
            topic_context="分数加法",
        )

    assert result["is_correct"] is False
    assert "分母" in result["feedback"]


@pytest.mark.asyncio
async def test_stream_chat(ai_tutor):
    chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="分数"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content="乘法"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content="就是"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content="..."))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),
    ]

    class MockStream:
        def __aiter__(self):
            self._iter = iter(chunks)
            return self

        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration

    mock_stream = MockStream()

    async def mock_create(*args, **kwargs):
        return mock_stream

    with patch.object(ai_tutor.client.chat.completions, "create", new=mock_create):
        collected = []
        async for chunk in ai_tutor.stream_response(
            messages=[{"role": "user", "content": "什么是分数乘法？"}],
        ):
            collected.append(chunk)

    assert "".join(collected) == "分数乘法就是..."
