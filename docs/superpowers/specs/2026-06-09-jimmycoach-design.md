# JimmyCoach — Design Spec

**Date:** 2026-06-09  
**Topic:** AI tutoring coach for Jimmy (6th→7th grade transition)

## Overview

JimmyCoach is a web-based AI coach that helps Jimmy, a 6th-grade student, consolidate elementary school knowledge and preview 7th-grade subjects, replacing external tutoring classes.

## Core Decisions

| Decision | Choice |
|---|---|
| **Platform** | Web app, single user (Jimmy only), no authentication |
| **Subjects** | 语文, 数学, 英语, 科学 |
| **Interaction** | Hybrid — structured lessons as backbone, chat interface on top |
| **AI Model** | DeepSeek API (deepseek-chat) |
| **Tech Stack** | Python — FastAPI + Jinja2 + Htmx + SQLite |
| **Content** | Hybrid — curriculum structure in YAML files, AI generates actual lesson content |

## Architecture

Single FastAPI process serving HTML pages, handling AJAX interactions via Htmx, and streaming AI responses via Server-Sent Events.

```
Browser → FastAPI Server → DeepSeek API
                   ↓
                SQLite DB + YAML curriculum files
```

### Components

- **Routes** (`routes/`): Thin HTTP handlers — parse request, call service, return response
- **Services** (`services/`): Business logic — curriculum loading, AI tutor calls, progress tracking, chat context
- **Database** (`db/`): SQLAlchemy ORM over SQLite, WAL mode for concurrent access
- **Templates** (`templates/`): Jinja2 server-side templates + Htmx partials for dynamic fragments
- **Curriculum** (`data/curriculum/`): YAML files defining topic tree, learning goals, exercise templates
- **Prompts** (`prompts/`): YAML system prompt templates for different AI modes

### Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Home page — subject overview + study suggestion |
| `/subjects/{id}` | GET | Subject detail — topic tree with progress |
| `/learn/{topic_id}` | GET | Lesson page — AI content + exercises + chat |
| `/chat/stream` | POST | SSE chat streaming |
| `/exercise/check` | POST | Submit answer, get AI grading |

### Services

- **CurriculumService**: Load and query YAML curriculum files
- **AITutorService**: DeepSeek API calls (streaming for lessons/chat, non-streaming for grading)
- **ProgressService**: Read/write study sessions, exercise attempts, topic mastery status
- **ChatContextService**: Build prompt context from recent history + current lesson

## Data Model

### SQLite Tables

- **study_sessions**: id, date, topic_id, duration_sec, completed, confidence_score
- **exercise_attempts**: id, session_id (FK), exercise_id, student_answer, is_correct, ai_feedback
- **chat_messages**: id, session_id (FK), role (user/assistant), content, created_at
- **progress_snapshots**: id, topic_id, status (not_started/in_progress/mastered), last_studied, attempts_count

### Curriculum YAML Structure

```
data/curriculum/
  grade6/
    math/
      topics.yaml        # Topic tree with order, dependencies, estimated time
      fractions/
        meta.yaml        # Learning goals, key points, common mistakes, teaching approach
        exercises.yaml   # Exercise templates per topic
    chinese/
    english/
    science/
  grade7/
    math/ ...
```

## AI Integration

### Call Patterns

| Mode | Model | Temp | Tokens | Stream |
|---|---|---|---|---|
| Generate Lesson | deepseek-chat | 0.7 | ~800 | Yes (SSE) |
| Grade Answer | deepseek-chat | 0.3 | ~200 | No |
| Chat Reply | deepseek-chat | 0.8 | ~300 | Yes (SSE) |

### Prompt Composition (3 Layers)

1. **Persona** (always): Base tutoring personality — patient, encouraging, 12-year-old appropriate language
2. **Mode-specific**: Teaching vs grading vs chatting instructions
3. **Dynamic context**: Current topic, recent chat history (last 10 msgs), exercise data, progress weaknesses

### Streaming Flow

```
Browser POST /chat/stream → FastAPI → DeepSeek stream=True
    → FastAPI StreamingResponse (text/event-stream)
    → Browser SSE → Htmx swaps characters in real-time
    → On complete: save full exchange to SQLite
```

## UI/UX Design

### Page Map

1. **Home (`/`)**: 4 subject cards with progress bars, "继续学习" suggestion
2. **Subject Detail (`/subjects/{id}`)**: Topic tree — completed (✅), current (🔵), locked (🔒)
3. **Lesson Page (`/learn/{topic_id}`)**: AI-generated content (top) → exercises (middle) → chat panel (bottom)
4. **Free Chat**: Standalone chat, not tied to a lesson

### Chat Modes

- **Embedded**: Docked at bottom of lesson page, context-aware (knows current topic)
- **Standalone**: Full-page chat, free-form questions

### User Flow

1. Jimmy opens app → Home with 4 subject cards
2. Clicks subject → Topic tree with progress
3. Clicks topic → Lesson loads (AI streams content)
4. Reads content, does exercises, gets AI-graded feedback
5. Asks questions in chat panel if confused
6. Session ends → Progress saved to SQLite

## Project Structure

```
jimmycoach/
  main.py              # FastAPI entry point
  config.py            # Settings (API key, DB path, etc.)
  routes/              # HTTP handlers (pages.py, chat.py, exercises.py)
  services/            # Business logic (curriculum.py, ai_tutor.py, progress.py, chat_context.py)
  db/                  # models.py, database.py
  templates/           # Jinja2 (base.html, home.html, subject.html, lesson.html) + partials/
  static/              # style.css, htmx.min.js
  data/curriculum/     # YAML curriculum files
  prompts/             # YAML system prompt templates
  tests/               # test_curriculum.py, test_ai_tutor.py, test_routes.py
  requirements.txt
```

### Dependencies

Python 3.11+ required.

```
fastapi[standard]        # Web framework + uvicorn
jinja2                   # Template engine
openai                   # DeepSeek API via OpenAI-compatible SDK
                        #   base_url=https://api.deepseek.com/v1
pyyaml                   # Curriculum & prompt files
sqlalchemy               # ORM for SQLite
pydantic-settings        # Config management (API key, DB path from env/file)
pytest                   # Testing
httpx                    # Async HTTP testing
```

## Error Handling

| Scenario | Response |
|---|---|
| DeepSeek API unavailable | Friendly message + retry button |
| Stream interrupted | Show partial response + reconnect prompt |
| Invalid curriculum YAML | Startup validation with clear error |
| Exercise missing answer | Skip grading, show encouragement |
| Empty chat input | Client-side prevention |

## Testing Strategy

- **Unit**: Curriculum parsing, prompt building, progress logic
- **Integration**: FastAPI TestClient for routes, mocked DeepSeek responses
- **Manual**: Walk through full user flow as Jimmy

## Out of Scope

- Multi-user support
- Authentication/authorization
- Parent monitoring dashboard
- Mobile app
- Offline mode
- Content authoring UI (curriculum edited as YAML files directly)
