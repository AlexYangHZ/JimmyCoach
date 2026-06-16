# JimmyCoach — Current Status (2026-06-16)

## What's Built

### Core Platform
- **FastAPI** app with Jinja2 + Htmx + SQLite
- **DeepSeek API** integration for content generation, grading, and RAG chat
- **29 tests** passing
- Modern responsive UI with gradient hero, card-based layouts, smooth animations
- GitHub: `git@github.com:AlexYangHZ/JimmyCoach.git`

### Math 七年级上册 ✅
- PDF split into 17 section PDFs, browser-native iframe viewer
- Mind maps for all 17 sections (interactive tree, save as PNG)
- Key formulas/concepts/tips displayed per knowledge point
- 85 pre-built exercises (choice, fill-in, true/false)
- All-exercises page with quick-jump nav, interactive answer checking
- Word (.docx) download for printable worksheets
- RAG TF-IDF retrieval (253 docs)
- Error book with per-subject tracking
- Study progress tracking + per-subject reset

### English 七年级上册 ✅
- 10 sections across 5 chapters (pipeline processed)
- **100 exercises** (10 per section: 4 choice + 4 fill + 2 true/false)
- Exercises reviewed, bugs fixed, language standardized to English
- Keypoints, mindmaps auto-generated via DeepSeek
- RAG TF-IDF retriever (37 docs)
- Word download now subject-aware (no longer hardcoded to math)

### RAG Chat (Redesigned 2026-06-16) ✅
- **Standalone `/chat` page** — moved from per-subject modal to unified entry
- **Multi-subject retrieval** — `search_all()` searches all available retrievers, merged by score
- **Score threshold filtering** (min_score=0.05), top_k: 3→5, truncation: 600→800 chars
- **Improved prompt** (`prompts/rag_chat.yaml`) — 小教练 persona + few-shot examples, "定义+例子+鼓励" format
- **Conversation history** — DB-persisted via `chat_messages` table, 6-turn context injection
- **Streaming SSE** with typewriter effect, source attribution
- **Subject selector** — default "全部科目" or pick specific subject
- temperature 0.7→0.3, max_tokens 500→800

### Admin Pipeline ✅
- Upload PDF → DeepSeek parses TOC → user confirms chapters → auto-generates:
  - PDF per-section split
  - Keypoints (concepts, formulas, tips)
  - Mind map data
  - 5 exercises per section (2 choice + 2 fill + 1 true/false)
  - TF-IDF retriever index with metadata
- Task list with SSE progress, status colors, delete
- Published content management with delete
- Drag-drop file upload, modal chapter confirmation
- Auto-discovery: subjects appear on home page automatically

### Code Quality
- ✅ 29 tests passing
- ✅ XSS protection, session isolation, async-safe retrievers
- ✅ CSS deduplication, shared constants, singleton AI service
- ✅ Chat history persisted to DB (survives restart)
- ✅ English exercise generation prompt + script (`prompts/exercise_gen_english.yaml`, `scripts/gen_english_ex.py`)

## Key Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI entry, static mounts, lifespan |
| `config.py` | Settings + shared constants |
| `routes/pages.py` | Home, subject, lesson, mindmap, dynamic catalog |
| `routes/chat.py` | Unified RAG chat — multi-retriever, DB history, SSE streaming |
| `routes/exercises.py` | Exercises, Word download, error book, reset |
| `routes/admin.py` | Pipeline management, upload, delete |
| `services/retriever.py` | TF-IDF + multi-subject search_all + score threshold |
| `services/ai_tutor.py` | DeepSeek API wrapper + singleton |
| `services/pipeline.py` | PDF→knowledge-point automated pipeline |
| `services/progress.py` | Study progress + chat session management |
| `templates/base.html` | Base layout with 💬 课程问答 nav link |
| `templates/home.html` | Hero + subject cards (no chat modal) |
| `templates/chat.html` | Standalone chat page with subject selector |
| `templates/admin.html` | Two-column admin with drag-drop |
| `prompts/rag_chat.yaml` | RAG system prompt — persona + few-shot + format rules |
| `prompts/exercise_gen_english.yaml` | English exercise generation prompt |
| `scripts/gen_english_ex.py` | Batch exercise generation via DeepSeek |
| `data/exercises/{subject}.json` | Per-subject exercise data |
| `data/keypoints/{subject}_grade7.json` | Per-subject key concepts |
| `data/mindmaps/{subject}_grade7.json` | Per-subject mind maps |
| `data/textbooks/{subject}/grade7/` | PDFs + sections.json + markdown |
| `data/vectordb/{subject}/retriever.pkl` | TF-IDF index per subject |

## How to Run

```bash
cd ~/projects/JimmyCoach
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
# Home: http://localhost:8000
# Chat: http://localhost:8000/chat
# Admin: http://localhost:8000/admin
```

## Next Steps

1. Chinese (语文) PDF processing — PDF uploaded, pipeline pending
2. ONNX Chinese embedding model for better semantic search
3. Mobile responsive refinements
