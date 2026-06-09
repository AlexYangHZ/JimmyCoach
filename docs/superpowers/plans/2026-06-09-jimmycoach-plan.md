# JimmyCoach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web-based AI tutoring coach for Jimmy (6th→7th grade) using FastAPI + Jinja2 + Htmx + SQLite with DeepSeek API.

**Architecture:** Single Python process — FastAPI serves HTML pages via Jinja2, dynamic interactions via Htmx AJAX, AI streaming via SSE. SQLite stores progress, YAML files define curriculum structure. DeepSeek API generates lesson content and grades exercises.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, Htmx 2.x, SQLite (SQLAlchemy), DeepSeek API (OpenAI-compatible SDK), PyYAML, Pydantic Settings

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `main.py` (skeleton)

- [ ] **Step 1: Create requirements.txt**

```text
fastapi[standard]==0.115.0
jinja2==3.1.4
openai==1.55.0
pyyaml==6.0.2
sqlalchemy==2.0.35
pydantic-settings==2.5.2
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Create config.py**

```python
"""Application configuration loaded from environment variables and .env file."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Database
    database_url: str = "sqlite+aiosqlite:///jimmycoach.db"

    # App
    app_name: str = "JimmyCoach"
    data_dir: Path = Path("data")
    prompts_dir: Path = Path("prompts")


settings = Settings()
```

- [ ] **Step 3: Create main.py (skeleton)**

```python
"""JimmyCoach — AI tutoring coach for Jimmy."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings

app = FastAPI(title=settings.app_name)

# Static files will be mounted after routes are registered
# Routes will be imported in later tasks


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 4: Install dependencies and verify**

Run: `cd /home/AlexYang/projects/JimmyCoach && pip install -r requirements.txt`
Expected: All packages install successfully.

Run: `python -c "from config import settings; print(settings.app_name)"`
Expected: `JimmyCoach`

- [ ] **Step 5: Create .env file**

```bash
echo "DEEPSEEK_API_KEY=your-key-here" > /home/AlexYang/projects/JimmyCoach/.env
echo ".env" >> /home/AlexYang/projects/JimmyCoach/.gitignore
echo "jimmycoach.db" >> /home/AlexYang/projects/JimmyCoach/.gitignore
echo "__pycache__/" >> /home/AlexYang/projects/JimmyCoach/.gitignore
echo ".superpowers/" >> /home/AlexYang/projects/JimmyCoach/.gitignore
```

- [ ] **Step 6: Create __init__.py files for all packages**

Run:
```bash
cd /home/AlexYang/projects/JimmyCoach
mkdir -p routes services db templates/partials static data/curriculum/grade6/math data/curriculum/grade6/chinese data/curriculum/grade6/english data/curriculum/grade6/science data/curriculum/grade7/math prompts tests
touch routes/__init__.py services/__init__.py db/__init__.py tests/__init__.py
```

- [ ] **Step 7: Init git and commit**

```bash
cd /home/AlexYang/projects/JimmyCoach
git init
git add -A
git commit -m "chore: project scaffolding

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Database Models & Setup

**Files:**
- Create: `db/models.py`
- Create: `db/database.py`

- [ ] **Step 1: Create db/database.py**

```python
"""Database connection and session management."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables. Called at application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Create db/models.py**

```python
"""SQLAlchemy ORM models for JimmyCoach."""

from datetime import datetime
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
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("StudySession", back_populates="messages")


class ProgressSnapshot(Base):
    __tablename__ = "progress_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(String(100), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default="not_started")  # not_started, in_progress, mastered
    last_studied = Column(DateTime, nullable=True)
    attempts_count = Column(Integer, default=0)
```

- [ ] **Step 3: Write tests for models**

Create `tests/test_models.py`:

```python
"""Test database models can be created and queried."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from db.models import Base, StudySession, ExerciseAttempt, ChatMessage, ProgressSnapshot


@pytest.fixture
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
    await db_session.refresh(session)

    assert len(session.exercises) == 1
    assert session.exercises[0].student_answer == "3/4"


@pytest.mark.asyncio
async def test_chat_message_relation(db_session):
    session = StudySession(date="2026-06-09", topic_id="fractions-multiply")
    db_session.add(session)
    await db_session.flush()

    msg = ChatMessage(session_id=session.id, role="user", content="什么是分数乘法？")
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(session)

    assert len(session.messages) == 1
    assert session.messages[0].role == "user"


@pytest.mark.asyncio
async def test_progress_snapshot_unique_topic(db_session):
    ps = ProgressSnapshot(topic_id="fractions-multiply", status="in_progress", attempts_count=3)
    db_session.add(ps)
    await db_session.commit()

    assert ps.id is not None
    assert ps.status == "in_progress"
```

- [ ] **Step 4: Run model tests**

Run: `cd /home/AlexYang/projects/JimmyCoach && pip install aiosqlite && python -m pytest tests/test_models.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add database models and setup

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Curriculum Service

**Files:**
- Create: `services/curriculum.py`
- Create: `data/curriculum/grade6/math/topics.yaml`
- Create: `data/curriculum/grade6/math/fractions-basics/meta.yaml`
- Create: `data/curriculum/grade6/math/fractions-basics/exercises.yaml`
- Create: `tests/test_curriculum.py`

- [ ] **Step 1: Create sample curriculum YAML data**

Create `data/curriculum/grade6/math/topics.yaml`:

```yaml
# 六年级下数学 — Topic tree
subject: 数学
grade: 6
topics:
  - id: fractions-basics
    title: 分数的基本性质
    order: 1
    dependencies: []
    estimated_minutes: 30
    key_points:
      - 分数的意义与读写
      - 真分数、假分数与带分数
      - 分数的基本性质

  - id: fractions-multiply
    title: 分数乘法
    order: 2
    dependencies: [fractions-basics]
    estimated_minutes: 45
    key_points:
      - 分数乘整数的意义与计算
      - 分数乘分数的计算方法
      - 分数乘法的简便运算

  - id: fractions-divide
    title: 分数除法
    order: 3
    dependencies: [fractions-multiply]
    estimated_minutes: 45
    key_points:
      - 倒数的概念
      - 分数除以整数的计算
      - 一个数除以分数的计算方法
```

Create `data/curriculum/grade6/math/fractions-basics/meta.yaml`:

```yaml
topic_id: fractions-basics
difficulty_level: 1
prerequisite_knowledge:
  - 整数除法
  - 除法的意义
common_mistakes:
  - 混淆分子和分母
  - 忘记约分
  - 假分数与带分数转换错误
teaching_approach: |
  用生活中的分物品例子引入分数的概念。
  先用图形（圆形、长方形）直观展示分数，再过渡到抽象计算。
  强调"平均分"是分数的核心概念。
```

Create `data/curriculum/grade6/math/fractions-basics/exercises.yaml`:

```yaml
topic_id: fractions-basics
exercises:
  - id: ex-01
    type: multiple_choice
    question: "下面哪个图形表示 3/4？"
    options:
      - "一个圆分成3份，取1份"
      - "一个圆分成4份，取3份"
      - "一个圆分成4份，取1份"
      - "一个圆分成3份，取3份"
    correct: "一个圆分成4份，取3份"
    hint: "分母表示分成几份，分子表示取几份"

  - id: ex-02
    type: fill_blank
    question: "把一根绳子平均分成5段，每段是这根绳子的___/___。"
    correct: "1/5"
    hint: "平均分成5段，每段就是1份，总共5份"

  - id: ex-03
    type: true_false
    question: "3/5的分子是5，分母是3。对吗？"
    correct: "错误"
    hint: "分数线上面是分子，下面是分母"
```

- [ ] **Step 2: Write the failing test for CurriculumService**

Create `tests/test_curriculum.py`:

```python
"""Test curriculum YAML loading and querying."""

import pytest
from pathlib import Path

from services.curriculum import CurriculumService


@pytest.fixture
def curriculum_service():
    data_dir = Path(__file__).parent.parent / "data" / "curriculum"
    return CurriculumService(data_dir=data_dir)


def test_load_topics_for_subject(curriculum_service):
    topics = curriculum_service.get_topics(grade=6, subject="math")

    assert len(topics) == 3
    assert topics[0]["id"] == "fractions-basics"
    assert topics[1]["id"] == "fractions-multiply"
    assert topics[2]["id"] == "fractions-divide"
    # Check ordering
    assert topics[0]["order"] == 1
    assert topics[2]["order"] == 3


def test_get_topic_meta(curriculum_service):
    meta = curriculum_service.get_topic_meta(grade=6, subject="math", topic_id="fractions-basics")

    assert meta["topic_id"] == "fractions-basics"
    assert meta["difficulty_level"] == 1
    assert "混淆分子和分母" in meta["common_mistakes"]


def test_get_exercises(curriculum_service):
    exercises = curriculum_service.get_exercises(grade=6, subject="math", topic_id="fractions-basics")

    assert len(exercises) == 3
    assert exercises[0]["id"] == "ex-01"
    assert exercises[0]["type"] == "multiple_choice"


def test_topic_dependencies(curriculum_service):
    topics = curriculum_service.get_topics(grade=6, subject="math")

    bas = curriculum_service.get_topic_by_id(topics, "fractions-basics")
    mul = curriculum_service.get_topic_by_id(topics, "fractions-multiply")

    assert bas["dependencies"] == []
    assert "fractions-basics" in mul["dependencies"]


def test_topic_by_id_not_found(curriculum_service):
    topics = curriculum_service.get_topics(grade=6, subject="math")
    result = curriculum_service.get_topic_by_id(topics, "nonexistent")

    assert result is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_curriculum.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.curriculum'`

- [ ] **Step 4: Implement CurriculumService**

Create `services/__init__.py` (touch if needed), then `services/curriculum.py`:

```python
"""Curriculum service — loads and queries YAML curriculum files."""

from pathlib import Path
from typing import Any
import yaml


class CurriculumService:
    """Loads curriculum data from YAML files on disk."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def _subject_dir(self, grade: int, subject: str) -> Path:
        return self.data_dir / f"grade{grade}" / subject

    def get_topics(self, grade: int, subject: str) -> list[dict[str, Any]]:
        """Return all topics for a grade/subject, sorted by order."""
        topics_path = self._subject_dir(grade, subject) / "topics.yaml"
        if not topics_path.exists():
            return []
        with open(topics_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        topics = data.get("topics", [])
        topics.sort(key=lambda t: t.get("order", 999))
        return topics

    def get_topic_meta(self, grade: int, subject: str, topic_id: str) -> dict[str, Any] | None:
        """Return learning goals and teaching notes for a topic."""
        meta_path = self._subject_dir(grade, subject) / topic_id / "meta.yaml"
        if not meta_path.exists():
            return None
        with open(meta_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_exercises(self, grade: int, subject: str, topic_id: str) -> list[dict[str, Any]]:
        """Return exercise templates for a topic."""
        ex_path = self._subject_dir(grade, subject) / topic_id / "exercises.yaml"
        if not ex_path.exists():
            return []
        with open(ex_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("exercises", [])

    @staticmethod
    def get_topic_by_id(topics: list[dict[str, Any]], topic_id: str) -> dict[str, Any] | None:
        """Find a topic dict in a topics list by id."""
        for t in topics:
            if t["id"] == topic_id:
                return t
        return None

    @staticmethod
    def get_next_topic(topics: list[dict[str, Any]], completed_ids: set[str]) -> dict[str, Any] | None:
        """Find the first topic not yet completed (respecting dependencies)."""
        for topic in topics:
            if topic["id"] in completed_ids:
                continue
            # Topic is available if all dependencies are completed
            if all(dep in completed_ids for dep in topic.get("dependencies", [])):
                return topic
        return None

    def list_subjects(self, grade: int) -> list[str]:
        """List all subjects available for a grade."""
        grade_dir = self.data_dir / f"grade{grade}"
        if not grade_dir.exists():
            return []
        return [d.name for d in grade_dir.iterdir() if d.is_dir()]

    def get_subject_name(self, subject_id: str) -> str:
        """Map subject id to Chinese display name."""
        names = {"math": "数学", "chinese": "语文", "english": "英语", "science": "科学"}
        return names.get(subject_id, subject_id)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_curriculum.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add curriculum service with YAML data loading

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: System Prompts

**Files:**
- Create: `prompts/tutor_base.yaml`
- Create: `prompts/lesson_teach.yaml`
- Create: `prompts/exercise_hint.yaml`
- Create: `prompts/exercise_grade.yaml`
- Create: `prompts/chat_free.yaml`

- [ ] **Step 1: Create all prompt YAML files**

Create `prompts/tutor_base.yaml`:

```yaml
id: tutor_base
description: Core persona and rules for the AI tutor
system: |
  你是一位耐心、鼓励性的AI辅导老师，名叫小教练。
  你的学生叫Jimmy，今年12岁，正在准备从六年级升入七年级。
  
  教学原则：
  - 用简单易懂的语言解释概念，避免过于学术化的表达
  - 多用生活中的例子帮助理解
  - 每次回复控制在200字以内，保持简洁
  - 使用适合12岁学生的语言，像朋友一样交流
  - 学生做对时真诚表扬，做错时温和鼓励
  - 永远不直接给出答案，先引导学生自己思考
  - 如果学生表现出沮丧，先安抚情绪再继续教学
```

Create `prompts/lesson_teach.yaml`:

```yaml
id: lesson_teach
description: System prompt for generating lesson/teaching content
system: |
  你正在给Jimmy讲解一个新知识点。请按以下结构生成教学内容：
  
  1. **引入**（1-2句）：用一个生活场景或有趣的问题引入话题
  2. **核心概念**（3-5句）：用简单语言解释关键概念，配合例子
  3. **例题演示**（1-2个）：逐步展示解题过程
  4. **要点总结**（1-2句）：记住最重要的1-2个要点
  
  注意：
  - 用日常语言，避免术语堆砌
  - 多使用"想象一下"、"比如"这样的引导语
  - 如果概念比较难，多用比喻
```

Create `prompts/exercise_hint.yaml`:

```yaml
id: exercise_hint
description: System prompt for giving hints on exercises without revealing the answer
system: |
  Jimmy在一道练习题上遇到困难。请给他一个提示，但不要直接告诉他答案。
  
  提示策略：
  - 指出他可能忽略的关键信息
  - 引导他回忆相关知识点
  - 用一个更简单的类似问题作为示范
  - 问他一个问题，帮助他自己发现解题思路
  
  绝对不要：
  - 直接说出正确答案
  - 说"答案就是..."
```

Create `prompts/exercise_grade.yaml`:

```yaml
id: exercise_grade
description: System prompt for grading student answers
system: |
  请评价Jimmy的答案。
  
  输出格式（严格遵循）：
  对错: [正确/错误/部分正确]
  反馈: [2-3句话的反馈]
  
  反馈要求：
  - 如果正确：具体表扬哪里做得好，为什么对
  - 如果错误：指出具体哪里出错了，但用鼓励的语气
  - 如果部分正确：先肯定对的部分，再指出需要改进的地方
```

Create `prompts/chat_free.yaml`:

```yaml
id: chat_free
description: System prompt for free-form chat tutoring
system: |
  Jimmy正在自由提问。请像一位耐心的家教老师一样回答他的问题。
  
  - 回答要简洁明了
  - 如果他问的是学习相关的问题，用例子帮助理解
  - 如果他感到焦虑（比如担心升学），给予鼓励
  - 如果他问与学习无关的问题，友好回应但温和地引导回学习话题
  - 保持轻松愉快的聊天氛围
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: add system prompt templates for AI tutor

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: AI Tutor Service

**Files:**
- Create: `services/ai_tutor.py`
- Create: `tests/test_ai_tutor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ai_tutor.py`:

```python
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
    """Teaching messages include persona + teach prompt + topic context."""
    topic_meta = {
        "topic_id": "fractions-basics",
        "difficulty_level": 1,
        "teaching_approach": "用生活中的分物品例子引入",
        "common_mistakes": ["混淆分子和分母"],
    }

    messages = ai_tutor.build_teach_messages(topic_meta)

    assert len(messages) >= 2  # system + user
    assert messages[0]["role"] == "system"
    assert "小教练" in messages[0]["content"]
    assert "fractions-basics" in messages[-1]["content"]


def test_build_grade_messages(ai_tutor):
    """Grading messages include persona + grade prompt + exercise context."""
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
    """Chat messages include persona + free chat prompt + history + user message."""
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
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[-1]["role"] == "user"
    assert "分数的基本性质" in messages[0]["content"]


@pytest.mark.asyncio
async def test_grade_answer(ai_tutor):
    """Grade answer should parse AI response into structured result."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="对错: 正确\n反馈: 做得很好！答案完全正确。"))
    ]

    with patch.object(ai_tutor.client.chat.completions, "create", return_value=mock_response):
        result = await ai_tutor.grade_answer(
            exercise={"question": "1+1=?", "correct": "2"},
            student_answer="2",
            topic_context="加法",
        )

    assert result["is_correct"] is True
    assert "做得很好" in result["feedback"]


@pytest.mark.asyncio
async def test_grade_answer_incorrect(ai_tutor):
    """Grade answer should detect incorrect answers from AI response."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="对错: 错误\n反馈: 再想想，分母不能直接相加哦。"))
    ]

    with patch.object(ai_tutor.client.chat.completions, "create", return_value=mock_response):
        result = await ai_tutor.grade_answer(
            exercise={"question": "1/2+1/3=?", "correct": "5/6"},
            student_answer="2/5",
            topic_context="分数加法",
        )

    assert result["is_correct"] is False
    assert "分母" in result["feedback"]


@pytest.mark.asyncio
async def test_stream_chat(ai_tutor):
    """Stream chat should yield content chunks from the API."""
    chunks = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="分数"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content="乘法"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content="就是"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content="..."))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),  # finish
    ]

    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = chunks

    with patch.object(ai_tutor.client.chat.completions, "create", return_value=mock_stream):
        collected = []
        async for chunk in ai_tutor.stream_response(
            messages=[{"role": "user", "content": "什么是分数乘法？"}],
        ):
            collected.append(chunk)

    assert "".join(collected) == "分数乘法就是..."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai_tutor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.ai_tutor'`

- [ ] **Step 3: Implement AITutorService**

Create `services/ai_tutor.py`:

```python
"""AI Tutor service — DeepSeek API integration for teaching, grading, and chat."""

from pathlib import Path
from typing import AsyncGenerator, Any
import re

import yaml
from openai import AsyncOpenAI


class AITutorService:
    """Handles all DeepSeek API interactions."""

    def __init__(self, api_key: str, base_url: str, model: str, prompts_dir: Path):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.prompts_dir = Path(prompts_dir)
        self._prompts: dict[str, str] = {}

    def _load_prompt(self, name: str) -> str:
        """Load a system prompt from YAML, caching in memory."""
        if name not in self._prompts:
            path = self.prompts_dir / f"{name}.yaml"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                self._prompts[name] = data.get("system", "")
            else:
                self._prompts[name] = ""
        return self._prompts[name]

    def build_teach_messages(self, topic_meta: dict[str, Any]) -> list[dict[str, str]]:
        """Build message list for generating lesson content."""
        persona = self._load_prompt("tutor_base")
        teach = self._load_prompt("lesson_teach")

        system_content = f"{persona}\n\n{teach}"
        user_content = (
            f"请讲解以下知识点：\n"
            f"主题：{topic_meta.get('topic_id', '')}\n"
            f"难度：{topic_meta.get('difficulty_level', 1)}\n"
            f"教学方法建议：{topic_meta.get('teaching_approach', '')}"
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def build_grade_messages(
        self, exercise: dict[str, Any], student_answer: str, topic_context: str
    ) -> list[dict[str, str]]:
        """Build message list for grading an answer."""
        persona = self._load_prompt("tutor_base")
        grade = self._load_prompt("exercise_grade")

        system_content = f"{persona}\n\n{grade}"
        user_content = (
            f"当前学习主题：{topic_context}\n\n"
            f"题目：{exercise.get('question', '')}\n"
            f"题目类型：{exercise.get('type', '')}\n"
            f"正确答案：{exercise.get('correct', '')}\n"
            f"Jimmy的答案：{student_answer}\n\n"
            f"请评价Jimmy的答案。"
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def build_chat_messages(
        self,
        user_message: str,
        chat_history: list[dict[str, str]],
        topic_context: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        """Build message list for free-form chat."""
        persona = self._load_prompt("tutor_base")
        chat_prompt = self._load_prompt("chat_free")

        context_text = ""
        if topic_context:
            context_text = f"\n当前正在学习：{topic_context.get('title', topic_context.get('topic_id', ''))}"

        system_content = f"{persona}\n\n{chat_prompt}{context_text}"

        messages = [{"role": "system", "content": system_content}]
        # Last 10 messages of history
        messages.extend(chat_history[-10:])
        messages.append({"role": "user", "content": user_message})

        return messages

    async def grade_answer(
        self, exercise: dict[str, Any], student_answer: str, topic_context: str
    ) -> dict[str, Any]:
        """Grade an answer and return structured result. Non-streaming."""
        messages = self.build_grade_messages(exercise, student_answer, topic_context)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
            stream=False,
        )

        content = response.choices[0].message.content or ""

        # Parse "对错: [正确/错误/部分正确]" line
        is_correct = None
        match = re.search(r"对错:\s*(正确|错误|部分正确)", content)
        if match:
            status = match.group(1)
            if status == "正确":
                is_correct = True
            elif status == "错误":
                is_correct = False
            # 部分正确 → None (partial)

        # Extract feedback after "反馈:"
        feedback = ""
        fb_match = re.search(r"反馈:\s*(.+)", content, re.DOTALL)
        if fb_match:
            feedback = fb_match.group(1).strip()

        return {"is_correct": is_correct, "feedback": feedback, "raw": content}

    async def stream_response(
        self, messages: list[dict[str, str]], temperature: float = 0.8, max_tokens: int = 800
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding content chunks."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai_tutor.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add AI tutor service with DeepSeek API integration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Progress Service & Chat Context Service

**Files:**
- Create: `services/progress.py`
- Create: `services/chat_context.py`
- Create: `tests/test_progress.py`

- [ ] **Step 1: Create ProgressService**

Create `services/progress.py`:

```python
"""Progress service — tracks Jimmy's study progress."""

from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import StudySession, ExerciseAttempt, ChatMessage, ProgressSnapshot


class ProgressService:
    """Read and write study progress data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_session(self, topic_id: str) -> int:
        """Create a new study session, return its ID."""
        session = StudySession(
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            topic_id=topic_id,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        # Upsert progress snapshot
        stmt = select(ProgressSnapshot).where(ProgressSnapshot.topic_id == topic_id)
        result = await self.db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if snapshot:
            snapshot.status = "in_progress"
            snapshot.last_studied = datetime.now(timezone.utc)
            snapshot.attempts_count += 1
        else:
            snapshot = ProgressSnapshot(
                topic_id=topic_id,
                status="in_progress",
                last_studied=datetime.now(timezone.utc),
                attempts_count=1,
            )
            self.db.add(snapshot)

        await self.db.commit()
        return session.id

    async def complete_session(self, session_id: int, confidence_score: int, duration_sec: int):
        """Mark a session as completed with confidence and duration."""
        session = await self.db.get(StudySession, session_id)
        if session:
            session.completed = True
            session.confidence_score = confidence_score
            session.duration_sec = duration_sec
            await self.db.commit()

    async def add_exercise_attempt(
        self, session_id: int, exercise_id: str, student_answer: str, is_correct: bool | None, ai_feedback: str
    ):
        """Record an exercise attempt."""
        attempt = ExerciseAttempt(
            session_id=session_id,
            exercise_id=exercise_id,
            student_answer=student_answer,
            is_correct=is_correct,
            ai_feedback=ai_feedback,
        )
        self.db.add(attempt)
        await self.db.commit()

    async def add_chat_message(self, session_id: int, role: str, content: str):
        """Save a chat message to the session."""
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(msg)
        await self.db.commit()

    async def get_chat_history(self, session_id: int) -> list[dict[str, str]]:
        """Get chat history for a session as list of {role, content} dicts."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        return [{"role": m.role, "content": m.content} for m in messages]

    async def get_progress_summary(self, subject_topics: list[dict]) -> list[dict]:
        """Merge topic list with progress status from DB."""
        topic_ids = [t["id"] for t in subject_topics]
        stmt = select(ProgressSnapshot).where(ProgressSnapshot.topic_id.in_(topic_ids))
        result = await self.db.execute(stmt)
        snapshots = {s.topic_id: s for s in result.scalars().all()}

        enriched = []
        for topic in subject_topics:
            snap = snapshots.get(topic["id"])
            enriched.append({
                **topic,
                "status": snap.status if snap else "not_started",
                "last_studied": snap.last_studied.isoformat() if snap and snap.last_studied else None,
                "attempts_count": snap.attempts_count if snap else 0,
            })
        return enriched

    async def get_last_session(self) -> StudySession | None:
        """Get the most recent study session for 'continue learning' feature."""
        stmt = select(StudySession).order_by(StudySession.id.desc()).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_topic_mastery_stats(self) -> dict[str, int]:
        """Return count of topics by status."""
        stmt = select(ProgressSnapshot)
        result = await self.db.execute(stmt)
        snapshots = result.scalars().all()

        counts = {"not_started": 0, "in_progress": 0, "mastered": 0}
        for s in snapshots:
            counts[s.status] = counts.get(s.status, 0) + 1
        return counts
```

- [ ] **Step 2: Create ChatContextService**

Create `services/chat_context.py`:

```python
"""Chat context service — builds conversation context for AI prompts."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LessonContext:
    """Context about what Jimmy is currently studying."""
    topic_id: str = ""
    topic_title: str = ""
    grade: int = 6
    subject: str = ""
    key_points: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)


class ChatContextService:
    """Manages conversation context for AI interactions."""

    @staticmethod
    def make_lesson_context(
        topic: dict[str, Any] | None,
        topic_meta: dict[str, Any] | None,
        grade: int = 6,
        subject: str = "",
    ) -> LessonContext:
        """Create a LessonContext from topic and meta data."""
        if topic is None:
            return LessonContext()

        return LessonContext(
            topic_id=topic.get("id", ""),
            topic_title=topic.get("title", ""),
            grade=grade,
            subject=subject,
            key_points=topic.get("key_points", []),
            common_mistakes=topic_meta.get("common_mistakes", []) if topic_meta else [],
        )

    @staticmethod
    def build_topic_context_text(ctx: LessonContext) -> str:
        """Render lesson context as a string for the AI prompt."""
        if not ctx.topic_id:
            return ""
        parts = [
            f"当前学习主题：{ctx.topic_title}",
            f"年级：{ctx.grade}年级",
        ]
        if ctx.key_points:
            parts.append(f"学习重点：{'、'.join(ctx.key_points)}")
        if ctx.common_mistakes:
            parts.append(f"常见错误：{'、'.join(ctx.common_mistakes)}")
        return "\n".join(parts)

    @staticmethod
    def context_for_chat(ctx: LessonContext) -> dict[str, Any] | None:
        """Build the context dict for AI chat messages, or None if empty."""
        if not ctx.topic_id:
            return None
        return {
            "topic_id": ctx.topic_id,
            "title": ctx.topic_title,
            "key_points": ctx.key_points,
        }
```

- [ ] **Step 3: Write tests for ProgressService**

Create `tests/test_progress.py`:

```python
"""Test progress service."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from db.models import Base
from services.progress import ProgressService


@pytest.fixture
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

    # Verify completion
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

    # First session
    sid1 = await svc.start_session("fractions-basics")
    await svc.complete_session(sid1, 3, 200)

    # Second session on same topic updates existing snapshot
    sid2 = await svc.start_session("fractions-basics")

    topics = [{"id": "fractions-basics", "title": "...", "order": 1, "dependencies": [], "key_points": []}]
    enriched = await svc.get_progress_summary(topics)
    assert enriched[0]["attempts_count"] == 2  # Upserted
```

- [ ] **Step 4: Run progress tests**

Run: `python -m pytest tests/test_progress.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add progress and chat context services

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Page Routes & Templates — Base + Home

**Files:**
- Create: `routes/pages.py`
- Create: `templates/base.html`
- Create: `templates/home.html`

- [ ] **Step 1: Create base template**

Create `templates/base.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}JimmyCoach{% endblock %}</title>
    <script src="/static/htmx.min.js"></script>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header class="app-header">
        <div class="header-inner">
            <a href="/" class="logo">🎓 Jimmy教练</a>
            <nav>
                <a href="/subjects/math/6">数学</a>
                <a href="/subjects/chinese/6">语文</a>
                <a href="/subjects/english/6">英语</a>
                <a href="/subjects/science/6">科学</a>
                <a href="/chat">💬 自由提问</a>
            </nav>
            <div id="streak-badge" class="streak">
                {% if streak_days %}🔥 连续学习 {{ streak_days }} 天{% endif %}
            </div>
        </div>
    </header>

    <main class="app-main">
        {% block content %}{% endblock %}
    </main>

    <footer class="app-footer">
        <p>Jimmy的学习伙伴 🤖</p>
    </footer>
</body>
</html>
```

- [ ] **Step 2: Download htmx.min.js**

Run:
```bash
curl -sL https://unpkg.com/htmx.org@2.0.3/dist/htmx.min.js -o /home/AlexYang/projects/JimmyCoach/static/htmx.min.js
```

- [ ] **Step 3: Create home template**

Create `templates/home.html`:

```html
{% extends "base.html" %}
{% block title %}Jimmy教练 — 首页{% endblock %}

{% block content %}
<div class="home-container">
    <section class="hero">
        <h1>你好，Jimmy！👋</h1>
        <p class="subtitle">今天想学习什么？</p>
        {% if suggested_topic %}
        <a href="/learn/{{ suggested_topic.subject }}/{{ suggested_topic.grade }}/{{ suggested_topic.id }}"
           class="btn-primary">
            📚 继续上次：{{ suggested_topic.title }}
        </a>
        {% endif %}
    </section>

    <section class="subject-grid">
        {% for subject in subjects %}
        <a href="/subjects/{{ subject.id }}/{{ subject.grade }}" class="subject-card">
            <div class="subject-icon">{{ subject.icon }}</div>
            <h2>{{ subject.name }}</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ subject.progress_pct }}%"></div>
            </div>
            <p class="progress-text">{{ subject.completed }} / {{ subject.total }} 个知识点</p>
        </a>
        {% endfor %}
    </section>
</div>
{% endblock %}
```

- [ ] **Step 4: Create page routes**

Create `routes/pages.py`:

```python
"""Page routes — serve HTML pages."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.curriculum import CurriculumService
from services.progress import ProgressService
from services.chat_context import ChatContextService
from config import settings

router = APIRouter()

# Shared service instances (no state, safe to reuse)
curriculum_service = CurriculumService(data_dir=settings.data_dir / "curriculum")

SUBJECTS_CONFIG = [
    {"id": "math", "name": "数学", "icon": "📐", "grade": 6},
    {"id": "chinese", "name": "语文", "icon": "📖", "grade": 6},
    {"id": "english", "name": "英语", "icon": "🌐", "grade": 6},
    {"id": "science", "name": "科学", "icon": "🔬", "grade": 6},
]


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    progress_svc = ProgressService(db)

    enriched_subjects = []
    suggested_topic = None

    for subj in SUBJECTS_CONFIG:
        topics = curriculum_service.get_topics(grade=subj["grade"], subject=subj["id"])
        enriched_topics = await progress_svc.get_progress_summary(topics)

        completed = sum(1 for t in enriched_topics if t["status"] == "mastered")
        total = len(enriched_topics)
        progress_pct = int(completed / total * 100) if total > 0 else 0

        enriched_subjects.append({
            **subj,
            "completed": completed,
            "total": total,
            "progress_pct": progress_pct,
        })

    # Find suggested "continue learning" topic
    last_session = await progress_svc.get_last_session()
    if last_session and not last_session.completed:
        # Find the topic in curriculum
        for subj in SUBJECTS_CONFIG:
            topics = curriculum_service.get_topics(grade=subj["grade"], subject=subj["id"])
            topic = curriculum_service.get_topic_by_id(topics, last_session.topic_id)
            if topic:
                suggested_topic = {
                    **topic,
                    "subject": subj["id"],
                    "grade": subj["grade"],
                }
                break

    return request.app.state.templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "subjects": enriched_subjects,
            "suggested_topic": suggested_topic,
            "streak_days": 0,  # Will be implemented later
        },
    )
```

- [ ] **Step 5: Update main.py to wire routes and templates**

Edit `main.py`:

```python
"""JimmyCoach — AI tutoring coach for Jimmy."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from config import settings
from db.database import init_db
from routes import pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, mount templates. Shutdown: nothing."""
    await init_db()
    app.state.templates = Jinja2Templates(directory="templates")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routes
app.include_router(pages.router)
```

- [ ] **Step 6: Test the home page renders**

First, create empty curriculum files for all subjects so the page doesn't crash:

```bash
cd /home/AlexYang/projects/JimmyCoach
for subject in chinese english science; do
    mkdir -p "data/curriculum/grade6/$subject"
    cat > "data/curriculum/grade6/$subject/topics.yaml" << 'YAML'
subject: test
grade: 6
topics: []
YAML
done
```

Run: `cd /home/AlexYang/projects/JimmyCoach && uvicorn main:app --host 0.0.0.0 --port 8000 &`
Wait 2 seconds, then:
Run: `curl -s http://localhost:8000/ | head -20`
Expected: HTML with "Jimmy教练" and subject cards.

Kill uvicorn: `kill %1 2>/dev/null || true`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add base template, home page, and page routes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Subject & Lesson Page Routes + Templates

**Files:**
- Create: `templates/subject.html`
- Create: `templates/lesson.html`
- Modify: `routes/pages.py`

- [ ] **Step 1: Create subject page template**

Create `templates/subject.html`:

```html
{% extends "base.html" %}
{% block title %}{{ subject_name }} — Jimmy教练{% endblock %}

{% block content %}
<div class="subject-container">
    <div class="breadcrumb">
        <a href="/">← 返回首页</a>
    </div>

    <h1>{{ subject_icon }} {{ subject_name }} · {{ grade }}年级</h1>

    <div class="topic-list">
        {% for topic in topics %}
        <div class="topic-item status-{{ topic.status }}">
            <div class="topic-number">{{ topic.order }}</div>
            <div class="topic-info">
                <h3>{{ topic.title }}</h3>
                <div class="topic-meta">
                    <span>⏱️ {{ topic.estimated_minutes }}分钟</span>
                    {% if topic.status == "mastered" %}
                        <span class="badge badge-done">✅ 已掌握</span>
                    {% elif topic.status == "in_progress" %}
                        <span class="badge badge-active">🔵 学习中</span>
                    {% elif topic.available %}
                        <a href="/learn/{{ subject }}/{{ grade }}/{{ topic.id }}" class="btn-start">开始学习</a>
                    {% else %}
                        <span class="badge badge-locked">🔒 需先完成前置知识点</span>
                    {% endif %}
                </div>
               {% if topic.key_points %}
                <div class="key-points">
                    {% for kp in topic.key_points %}
                    <span class="kp-tag">{{ kp }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Create lesson page template**

Create `templates/lesson.html`:

```html
{% extends "base.html" %}
{% block title %}{{ topic.title }} — Jimmy教练{% endblock %}

{% block content %}
<div class="lesson-container">
    <div class="breadcrumb">
        <a href="/">首页</a> → <a href="/subjects/{{ subject }}/{{ grade }}">{{ subject_name }}</a> → {{ topic.title }}
    </div>

    <!-- Lesson content area — AI-streamed content -->
    <div id="lesson-content" class="lesson-content"
         hx-post="/learn/{{ subject }}/{{ grade }}/{{ topic.id }}/generate"
         hx-trigger="load"
         hx-swap="innerHTML">
        <div class="loading">
            <p>🤔 小教练正在准备这节课的内容...</p>
            <div class="spinner"></div>
        </div>
    </div>

    <!-- Exercises area -->
    <div id="exercises-area" class="exercises-section">
        <h2>📝 练习时间</h2>
        <div id="exercise-container"
             hx-get="/learn/{{ subject }}/{{ grade }}/{{ topic.id }}/exercises"
             hx-trigger="load"
             hx-swap="innerHTML">
            <p>加载练习题中...</p>
        </div>
    </div>

    <!-- Chat panel — always at bottom -->
    <div id="chat-panel" class="chat-panel">
        <div class="chat-header" onclick="document.getElementById('chat-messages').classList.toggle('expanded')">
            💬 有疑问？问我！
        </div>
        <div id="chat-messages" class="chat-messages"
             hx-get="/chat/history?topic={{ topic.id }}"
             hx-trigger="load"
             hx-swap="innerHTML">
        </div>
        <form class="chat-input-form"
              hx-post="/chat/send"
              hx-target="#chat-messages"
              hx-swap="beforeend"
              hx-on::after-request="this.reset()">
            <input type="hidden" name="topic_id" value="{{ topic.id }}">
            <input type="hidden" name="subject" value="{{ subject }}">
            <input type="hidden" name="grade" value="{{ grade }}">
            <input type="text" name="message" placeholder="输入你的问题..." required autocomplete="off"
                   class="chat-input">
            <button type="submit" class="btn-send">发送</button>
        </form>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Add subject and lesson routes to routes/pages.py**

Append to `routes/pages.py`:

```python

@router.get("/subjects/{subject}/{grade}", response_class=HTMLResponse)
async def subject_page(
    request: Request,
    subject: str,
    grade: int,
    db: AsyncSession = Depends(get_db),
):
    progress_svc = ProgressService(db)
    topics = curriculum_service.get_topics(grade=grade, subject=subject)
    enriched = await progress_svc.get_progress_summary(topics)

    # Determine which topics are available (dependencies met)
    completed_ids = {t["id"] for t in enriched if t["status"] == "mastered"}
    for topic in enriched:
        deps = topic.get("dependencies", [])
        topic["available"] = all(d in completed_ids for d in deps)

    return request.app.state.templates.TemplateResponse(
        "subject.html",
        {
            "request": request,
            "subject": subject,
            "grade": grade,
            "subject_name": curriculum_service.get_subject_name(subject),
            "subject_icon": {"math": "📐", "chinese": "📖", "english": "🌐", "science": "🔬"}.get(subject, "📚"),
            "topics": enriched,
            "streak_days": 0,
        },
    )


@router.get("/learn/{subject}/{grade}/{topic_id}", response_class=HTMLResponse)
async def lesson_page(
    request: Request,
    subject: str,
    grade: int,
    topic_id: str,
    db: AsyncSession = Depends(get_db),
):
    topics = curriculum_service.get_topics(grade=grade, subject=subject)
    topic = curriculum_service.get_topic_by_id(topics, topic_id)
    topic_meta = curriculum_service.get_topic_meta(grade=grade, subject=subject, topic_id=topic_id)

    if not topic:
        return HTMLResponse("Topic not found", status_code=404)

    # Start a study session
    progress_svc = ProgressService(db)
    session_id = await progress_svc.start_session(topic_id)

    return request.app.state.templates.TemplateResponse(
        "lesson.html",
        {
            "request": request,
            "subject": subject,
            "grade": grade,
            "topic": topic,
            "topic_meta": topic_meta,
            "session_id": session_id,
            "subject_name": curriculum_service.get_subject_name(subject),
            "streak_days": 0,
        },
    )
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add subject and lesson page routes and templates

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Chat Routes with SSE Streaming

**Files:**
- Create: `routes/chat.py`
- Modify: `main.py` (register chat routes)

- [ ] **Step 1: Create chat routes**

Create `routes/chat.py`:

```python
"""Chat routes — chat messaging and history."""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.ai_tutor import AITutorService
from services.progress import ProgressService
from services.chat_context import ChatContextService, LessonContext
from services.curriculum import CurriculumService
from config import settings

router = APIRouter()

ai_tutor = AITutorService(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    model=settings.deepseek_model,
    prompts_dir=settings.prompts_dir,
)
curriculum_service = CurriculumService(data_dir=settings.data_dir / "curriculum")


@router.post("/chat/send", response_class=HTMLResponse)
async def chat_send(
    request: Request,
    message: str = Form(...),
    topic_id: str = Form(""),
    subject: str = Form(""),
    grade: int = Form(6),
    db: AsyncSession = Depends(get_db),
):
    """Send a chat message and get AI response as HTML partial. Non-streaming for MVP."""
    progress_svc = ProgressService(db)

    # Build context
    ctx = LessonContext()
    if topic_id and subject:
        topics = curriculum_service.get_topics(grade=grade, subject=subject)
        topic = curriculum_service.get_topic_by_id(topics, topic_id)
        topic_meta = curriculum_service.get_topic_meta(grade=grade, subject=subject, topic_id=topic_id)
        ctx = ChatContextService.make_lesson_context(topic, topic_meta, grade, subject)

    # Get or create session
    last_session = await progress_svc.get_last_session()
    session_id = last_session.id if last_session else None
    if not session_id:
        session_id = await progress_svc.start_session(topic_id or "free-chat")

    chat_history = await progress_svc.get_chat_history(session_id)

    # Build AI messages
    context_dict = ChatContextService.context_for_chat(ctx)
    messages = ai_tutor.build_chat_messages(
        user_message=message,
        chat_history=chat_history,
        topic_context=context_dict,
    )

    # Save user message
    await progress_svc.add_chat_message(session_id, "user", message)

    # Get AI response (non-streaming)
    try:
        response = await ai_tutor.client.chat.completions.create(
            model=ai_tutor.model,
            messages=messages,
            temperature=0.8,
            max_tokens=300,
            stream=False,
        )
        reply = response.choices[0].message.content or "..."
    except Exception:
        reply = "😔 老师有点忙，请稍后再试。"

    await progress_svc.add_chat_message(session_id, "assistant", reply)

    # Return both user msg and assistant reply as HTML partials
    return HTMLResponse(
        f'<div class="chat-msg msg-user">'
        f'<span class="msg-avatar">🧑</span>'
        f'<span class="msg-content">{message}</span>'
        f'</div>'
        f'<div class="chat-msg msg-assistant">'
        f'<span class="msg-avatar">🤖</span>'
        f'<span class="msg-content">{reply}</span>'
        f'</div>'
    )


@router.get("/chat", response_class=HTMLResponse)
async def free_chat_page(request: Request):
    """Standalone free chat page, not tied to a lesson."""
    return request.app.state.templates.TemplateResponse(
        "free_chat.html",
        {"request": request, "streak_days": 0},
    )


@router.get("/chat/history", response_class=HTMLResponse)
async def chat_history(
    topic: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Return recent chat messages as HTML partial."""
    progress_svc = ProgressService(db)
    last_session = await progress_svc.get_last_session()
    if not last_session:
        return HTMLResponse('<div class="chat-empty"><p>👋 你好！有什么问题尽管问我。</p></div>')

    history = await progress_svc.get_chat_history(last_session.id)
    if not history:
        return HTMLResponse('<div class="chat-empty"><p>👋 你好！有什么问题尽管问我。</p></div>')

    html_parts = []
    for msg in history[-20:]:  # Last 20 messages
        role_class = "msg-assistant" if msg["role"] == "assistant" else "msg-user"
        avatar = "🤖" if msg["role"] == "assistant" else "🧑"
        html_parts.append(
            f'<div class="chat-msg {role_class}">'
            f'<span class="msg-avatar">{avatar}</span>'
            f'<span class="msg-content">{msg["content"]}</span>'
            f'</div>'
        )

    return HTMLResponse("".join(html_parts))
```

- [ ] **Step 2: Create free_chat.html template**

Create `templates/free_chat.html`:

```html
{% extends "base.html" %}
{% block title %}自由提问 — Jimmy教练{% endblock %}

{% block content %}
<div class="chat-standalone">
    <h1>💬 自由提问</h1>
    <p class="subtitle">有什么想问的？任何学习问题都可以！</p>

    <div id="chat-messages" class="chat-messages expanded"
         hx-get="/chat/history"
         hx-trigger="load"
         hx-swap="innerHTML">
    </div>

    <form class="chat-input-form"
          hx-post="/chat/send"
          hx-target="#chat-messages"
          hx-swap="beforeend"
          hx-on::after-request="this.reset()">
        <input type="hidden" name="topic_id" value="free-chat">
        <input type="text" name="message" placeholder="随便聊聊..." required autocomplete="off"
               class="chat-input">
        <button type="submit" class="btn-send">发送</button>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 3: Register chat routes in main.py**

Edit `main.py` — add import and router registration:

```python
from routes import pages, chat

# ... after app = FastAPI(...) and static mount ...

app.include_router(pages.router)
app.include_router(chat.router)
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add chat routes with non-streaming messaging

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Exercise Routes

**Files:**
- Create: `routes/exercises.py`
- Modify: `main.py` (register exercise routes)
- Create: `templates/partials/lesson_content.html`
- Create: `templates/partials/exercise_card.html`

- [ ] **Step 1: Create exercise routes**

Create `routes/exercises.py`:

```python
"""Exercise routes — generate lessons, load exercises, grade answers."""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.ai_tutor import AITutorService
from services.progress import ProgressService
from services.curriculum import CurriculumService
from config import settings

router = APIRouter()

ai_tutor = AITutorService(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    model=settings.deepseek_model,
    prompts_dir=settings.prompts_dir,
)
curriculum_service = CurriculumService(data_dir=settings.data_dir / "curriculum")


@router.post("/learn/{subject}/{grade}/{topic_id}/generate", response_class=HTMLResponse)
async def generate_lesson(
    subject: str,
    grade: int,
    topic_id: str,
):
    """Generate AI lesson content as an HTML partial."""
    topic_meta = curriculum_service.get_topic_meta(grade=grade, subject=subject, topic_id=topic_id)
    topics = curriculum_service.get_topics(grade=grade, subject=subject)
    topic = curriculum_service.get_topic_by_id(topics, topic_id)

    if not topic_meta:
        return HTMLResponse('<div class="error">课程内容未找到</div>')

    messages = ai_tutor.build_teach_messages(topic_meta)

    try:
        # Non-streaming for lesson generation (simpler, content is longer)
        response = await ai_tutor.client.chat.completions.create(
            model=ai_tutor.model,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
            stream=False,
        )
        content = response.choices[0].message.content or "课程内容生成中..."

        # Convert markdown-like content to HTML paragraphs
        html_paragraphs = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("**") and "**" in line[2:]:
                # Bold headings
                html_paragraphs.append(f'<h3 class="lesson-heading">{line.strip("* ")}</h3>')
            elif line.startswith("#"):
                html_paragraphs.append(f'<h3 class="lesson-heading">{line.lstrip("# ")}</h3>')
            else:
                html_paragraphs.append(f"<p>{line}</p>")

        return HTMLResponse("".join(html_paragraphs))

    except Exception as e:
        return HTMLResponse(
            '<div class="error">😔 课程内容生成失败，请检查网络连接后重试。</div>'
        )


@router.get("/learn/{subject}/{grade}/{topic_id}/exercises", response_class=HTMLResponse)
async def load_exercises(
    subject: str,
    grade: int,
    topic_id: str,
):
    """Load exercise templates as HTML partial."""
    exercises = curriculum_service.get_exercises(grade=grade, subject=subject, topic_id=topic_id)

    if not exercises:
        return HTMLResponse('<p>暂无练习题</p>')

    html_parts = []
    for ex in exercises:
        ex_id = ex["id"]
        q_type = ex.get("type", "")

        html_parts.append(f'<div class="exercise-card" id="exercise-{ex_id}">')
        html_parts.append(f'<p class="exercise-question"><strong>题目：</strong>{ex["question"]}</p>')

        if q_type == "multiple_choice":
            html_parts.append('<div class="exercise-options">')
            for i, opt in enumerate(ex.get("options", [])):
                letter = chr(65 + i)  # A, B, C, D
                html_parts.append(
                    f'<button class="btn-option" '
                    f'hx-post="/exercise/check" '
                    f'hx-vals=\'{{"exercise_id":"{ex_id}","answer":"{opt}","topic_id":"{topic_id}"}}\' '
                    f'hx-target="#exercise-{ex_id}" '
                    f'hx-swap="outerHTML">'
                    f'{letter}. {opt}</button>'
                )
            html_parts.append('</div>')
        elif q_type == "fill_blank":
            html_parts.append(
                f'<form hx-post="/exercise/check" hx-target="#exercise-{ex_id}" hx-swap="outerHTML" class="exercise-form">'
                f'<input type="hidden" name="exercise_id" value="{ex_id}">'
                f'<input type="hidden" name="topic_id" value="{topic_id}">'
                f'<input type="text" name="answer" placeholder="请输入你的答案" class="exercise-input" required>'
                f'<button type="submit" class="btn-submit">提交</button>'
                f'</form>'
            )
        elif q_type == "true_false":
            html_parts.append('<div class="exercise-options">')
            for ans in ["正确", "错误"]:
                html_parts.append(
                    f'<button class="btn-option" '
                    f'hx-post="/exercise/check" '
                    f'hx-vals=\'{{"exercise_id":"{ex_id}","answer":"{ans}","topic_id":"{topic_id}"}}\' '
                    f'hx-target="#exercise-{ex_id}" '
                    f'hx-swap="outerHTML">'
                    f'{ans}</button>'
                )
            html_parts.append('</div>')

        html_parts.append('</div>')

    return HTMLResponse("".join(html_parts))


@router.post("/exercise/check", response_class=HTMLResponse)
async def check_exercise(
    exercise_id: str = Form(...),
    answer: str = Form(...),
    topic_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Grade an exercise answer and return feedback as HTML partial."""
    # Find the exercise in curriculum
    exercises = []
    for subject in ["math", "chinese", "english", "science"]:
        for grade in [6, 7]:
            exs = curriculum_service.get_exercises(grade=grade, subject=subject, topic_id=topic_id)
            if exs:
                exercises = exs
                break

    exercise = None
    for ex in exercises:
        if ex["id"] == exercise_id:
            exercise = ex
            break

    if not exercise:
        return HTMLResponse('<div class="feedback-error">题目未找到</div>')

    # Grade via AI
    result = await ai_tutor.grade_answer(
        exercise=exercise,
        student_answer=answer,
        topic_context=topic_id,
    )

    # Save attempt
    progress_svc = ProgressService(db)
    last_session = await progress_svc.get_last_session()
    if last_session:
        await progress_svc.add_exercise_attempt(
            session_id=last_session.id,
            exercise_id=exercise_id,
            student_answer=answer,
            is_correct=result["is_correct"],
            ai_feedback=result["feedback"],
        )

    # Build feedback HTML
    if result["is_correct"] is True:
        status_icon = "✅"
        status_class = "feedback-correct"
    elif result["is_correct"] is False:
        status_icon = "❌"
        status_class = "feedback-incorrect"
    else:
        status_icon = "🤔"
        status_class = "feedback-partial"

    return HTMLResponse(
        f'<div class="exercise-card {status_class}" id="exercise-{exercise_id}">'
        f'<p class="exercise-question"><strong>题目：</strong>{exercise["question"]}</p>'
        f'<p><strong>你的答案：</strong>{answer}</p>'
        f'<div class="feedback">{status_icon} {result["feedback"]}</div>'
        f'</div>'
    )
```

- [ ] **Step 2: Register exercise routes in main.py**

Edit `main.py`:

```python
from routes import pages, chat, exercises

# ... add:
app.include_router(exercises.router)
```

- [ ] **Step 3: Create lesson content partial template**

Create `templates/partials/lesson_content.html`:

```html
<!-- Used as fallback / reference -- actual content is generated by AI -->
<article class="lesson-article">
    {{ content | safe }}
</article>
```

- [ ] **Step 4: Create exercise card partial template**

Create `templates/partials/exercise_card.html`:

```html
<div class="exercise-card" id="exercise-{{ exercise.id }}">
    <p class="exercise-question"><strong>{{ exercise.question }}</strong></p>
    <!-- Exercise interaction is handled by routes/exercises.py -->
</div>
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add exercise routes for lesson generation and grading

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Static Files & Styling

**Files:**
- Create: `static/style.css`

- [ ] **Step 1: Create stylesheet**

Create `static/style.css`:

```css
/* === Reset & Base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --primary: #4a90d9;
    --primary-dark: #357abd;
    --success: #27ae60;
    --warning: #f39c12;
    --danger: #e74c3c;
    --bg: #f5f7fa;
    --card-bg: #ffffff;
    --text: #2c3e50;
    --text-light: #7f8c8d;
    --border: #e1e8ed;
    --radius: 12px;
    --shadow: 0 2px 8px rgba(0,0,0,0.08);
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }

/* === Header === */
.app-header {
    background: var(--card-bg);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.header-inner {
    max-width: 960px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}
.logo {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--primary);
}
.header-inner nav { display: flex; gap: 16px; }
.header-inner nav a {
    color: var(--text);
    font-size: 0.9rem;
    padding: 4px 8px;
    border-radius: 6px;
    transition: background 0.2s;
}
.header-inner nav a:hover { background: #eef2f7; text-decoration: none; }
.streak { font-size: 0.85rem; color: var(--warning); }

/* === Main === */
.app-main {
    flex: 1;
    max-width: 960px;
    margin: 0 auto;
    padding: 24px;
    width: 100%;
}

/* === Home === */
.hero {
    text-align: center;
    padding: 40px 0 24px;
}
.hero h1 { font-size: 2rem; margin-bottom: 8px; }
.subtitle { color: var(--text-light); font-size: 1.1rem; }
.btn-primary {
    display: inline-block;
    margin-top: 16px;
    padding: 12px 32px;
    background: var(--primary);
    color: white;
    border-radius: 24px;
    font-size: 1.05rem;
    font-weight: 600;
    transition: background 0.2s, transform 0.1s;
}
.btn-primary:hover { background: var(--primary-dark); text-decoration: none; transform: scale(1.02); }

.subject-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-top: 24px;
}
.subject-card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 24px;
    text-align: center;
    box-shadow: var(--shadow);
    transition: transform 0.15s, box-shadow 0.15s;
    display: block;
    color: var(--text);
}
.subject-card:hover { transform: translateY(-3px); box-shadow: 0 4px 16px rgba(0,0,0,0.12); text-decoration: none; }
.subject-icon { font-size: 2.5rem; margin-bottom: 8px; }
.subject-card h2 { font-size: 1.2rem; margin-bottom: 12px; }

.progress-bar {
    height: 8px;
    background: var(--border);
    border-radius: 4px;
    overflow: hidden;
    margin: 8px 0;
}
.progress-fill {
    height: 100%;
    background: var(--success);
    border-radius: 4px;
    transition: width 0.5s ease;
}
.progress-text { font-size: 0.8rem; color: var(--text-light); }

/* === Subject (Topic Tree) === */
.breadcrumb { margin-bottom: 20px; font-size: 0.9rem; color: var(--text-light); }

.topic-list { display: flex; flex-direction: column; gap: 12px; }

.topic-item {
    display: flex;
    gap: 16px;
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
    align-items: flex-start;
}
.topic-number {
    width: 36px; height: 36px;
    background: var(--primary);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
    flex-shrink: 0;
}
.topic-item.status-mastered .topic-number { background: var(--success); }
.topic-item.status-in_progress .topic-number { background: var(--warning); }

.topic-info { flex: 1; }
.topic-info h3 { font-size: 1.1rem; margin-bottom: 8px; }
.topic-meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 0.85rem; }

.badge { padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; }
.badge-done { background: #e8f5e9; color: var(--success); }
.badge-active { background: #fff3e0; color: var(--warning); }
.badge-locked { background: #f5f5f5; color: var(--text-light); }

.btn-start {
    padding: 6px 18px;
    background: var(--primary);
    color: white;
    border-radius: 16px;
    font-size: 0.85rem;
    font-weight: 600;
}
.btn-start:hover { background: var(--primary-dark); text-decoration: none; }

.key-points { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.kp-tag {
    padding: 2px 10px;
    background: #eef2f7;
    border-radius: 10px;
    font-size: 0.8rem;
    color: var(--text-light);
}

/* === Lesson === */
.lesson-content { margin: 24px 0; }
.lesson-content p { margin-bottom: 12px; }
.lesson-heading { margin: 20px 0 8px; color: var(--primary); }
.loading { text-align: center; padding: 40px; color: var(--text-light); }
.spinner {
    width: 32px; height: 32px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 12px auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* === Exercises === */
.exercises-section { margin: 32px 0; }
.exercises-section h2 { margin-bottom: 16px; }

.exercise-card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 12px;
    box-shadow: var(--shadow);
}
.exercise-question { margin-bottom: 12px; font-size: 1.05rem; }

.exercise-options { display: flex; flex-wrap: wrap; gap: 8px; }
.btn-option {
    padding: 10px 18px;
    border: 2px solid var(--border);
    border-radius: 8px;
    background: white;
    cursor: pointer;
    font-size: 0.95rem;
    transition: all 0.15s;
}
.btn-option:hover { border-color: var(--primary); background: #eef6ff; }

.exercise-form { display: flex; gap: 8px; align-items: center; }
.exercise-input {
    flex: 1;
    padding: 10px 14px;
    border: 2px solid var(--border);
    border-radius: 8px;
    font-size: 0.95rem;
}
.exercise-input:focus { outline: none; border-color: var(--primary); }
.btn-submit {
    padding: 10px 24px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 0.95rem;
    cursor: pointer;
}
.btn-submit:hover { background: var(--primary-dark); }

.feedback-correct { border-left: 4px solid var(--success); }
.feedback-incorrect { border-left: 4px solid var(--danger); }
.feedback-partial { border-left: 4px solid var(--warning); }
.feedback { margin-top: 12px; padding: 8px 12px; background: #f8f9fa; border-radius: 8px; font-size: 0.95rem; }

/* === Chat Panel === */
.chat-panel {
    margin-top: 32px;
    background: var(--card-bg);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
}
.chat-header {
    background: var(--primary);
    color: white;
    padding: 12px 20px;
    cursor: pointer;
    font-weight: 600;
    user-select: none;
}
.chat-messages {
    padding: 16px;
    max-height: 300px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.chat-messages.expanded { max-height: 500px; }

.chat-msg { display: flex; gap: 8px; align-items: flex-start; font-size: 0.95rem; }
.msg-avatar { flex-shrink: 0; font-size: 1.2rem; }
.msg-content { line-height: 1.5; }
.msg-assistant .msg-content { background: #eef2f7; padding: 10px 14px; border-radius: 0 12px 12px 12px; }
.msg-user { flex-direction: row-reverse; }
.msg-user .msg-content { background: #dbeafe; padding: 10px 14px; border-radius: 12px 0 12px 12px; }

.chat-input-form {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid var(--border);
}
.chat-input {
    flex: 1;
    padding: 10px 14px;
    border: 2px solid var(--border);
    border-radius: 20px;
    font-size: 0.95rem;
}
.chat-input:focus { outline: none; border-color: var(--primary); }
.btn-send {
    padding: 10px 20px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    font-weight: 600;
}
.btn-send:hover { background: var(--primary-dark); }

.chat-empty { text-align: center; color: var(--text-light); padding: 20px; }

/* === Error === */
.error { color: var(--danger); padding: 20px; text-align: center; }

/* === Footer === */
.app-footer {
    text-align: center;
    padding: 16px;
    color: var(--text-light);
    font-size: 0.85rem;
    border-top: 1px solid var(--border);
    margin-top: 40px;
}
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: add CSS styling for all pages

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Integration — Final Wiring and Route Tests

**Files:**
- Create: `tests/test_routes.py`
- Modify: `main.py` (final review)

- [ ] **Step 1: Write route integration tests**

Create `tests/test_routes.py`:

```python
"""Integration tests for HTTP routes."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

# Set environment before importing app
import os
os.environ["DEEPSEEK_API_KEY"] = "test-key-for-integration"


@pytest.fixture
async def client():
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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
async def test_subject_page_404_for_invalid(client):
    response = await client.get("/subjects/nonexistent/6")
    assert response.status_code == 200  # Doesn't throw, shows empty topic list


@pytest.mark.asyncio
async def test_static_files_mounted(client):
    response = await client.get("/static/style.css")
    assert response.status_code == 200
    assert "box-sizing" in response.text
```

- [ ] **Step 2: Run route tests**

Run: `python -m pytest tests/test_routes.py -v`
Expected: All 7 tests PASS (or some may fail if DB path issue — fix DB path to use `:memory:` for tests).

- [ ] **Step 3: Final main.py review**

Ensure `main.py` looks like:

```python
"""JimmyCoach — AI tutoring coach for Jimmy."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from config import settings
from db.database import init_db
from routes import pages, chat, exercises


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.templates = Jinja2Templates(directory="templates")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(chat.router)
app.include_router(exercises.router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 5: Manual smoke test**

```bash
cd /home/AlexYang/projects/JimmyCoach
# Check the app starts
timeout 5 uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 || true
```
Expected: "Uvicorn running on http://0.0.0.0:8000"

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: final integration — wire all routes, add integration tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Implementation Order

Execute tasks in numerical order (1 → 12). Each task builds on the previous:

1. **Scaffolding** (Task 1) — project skeleton
2. **Database** (Task 2) — models and setup
3. **Curriculum** (Task 3) — YAML loading + sample data
4. **Prompts** (Task 4) — AI system prompt templates
5. **AI Service** (Task 5) — DeepSeek integration
6. **Progress & Context** (Task 6) — tracking and context services
7. **Pages — Home** (Task 7) — home page + htmx download
8. **Pages — Subject & Lesson** (Task 8) — topic tree + lesson templates
9. **Chat** (Task 9) — SSE streaming chat
10. **Exercises** (Task 10) — lesson generation + grading
11. **Styling** (Task 11) — CSS
12. **Integration** (Task 12) — final wiring + tests + smoke test

## After Implementation

Once all tasks are complete:
1. Set your DeepSeek API key in `.env`: `DEEPSEEK_API_KEY=sk-your-real-key`
2. Start the app: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. Open `http://localhost:8000` in a browser
4. Add more curriculum data for 语文, 英语, 科学, and grade 7 subjects
