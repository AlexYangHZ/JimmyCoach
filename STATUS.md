# JimmyCoach — Current Status (2026-06-11)

## What's Built

### Core Platform
- **FastAPI** app with Jinja2 + Htmx + SQLite
- **DeepSeek API** integration for content generation, grading, and RAG chat
- **28 tests** passing
- Modern responsive UI with gradient hero, card-based layouts, smooth animations

### Math 七年级上册 ✅
- PDF split into 17 section PDFs, browser-native iframe viewer
- Mind maps for all 17 sections (interactive tree, save as PNG)
- Key formulas/concepts/tips displayed prominently per knowledge point
- 85 pre-built exercises across all sections (choice, fill-in, true/false)
- All-exercises page with quick-jump nav, interactive answer checking
- Word (.docx) download for printable worksheets
- RAG chat — per-subject TF-IDF retrieval (253 docs), DeepSeek with source attribution
- Chat modal with streaming typewriter effect, history saved per-subject
- Error book with interactive answer mode, per-subject tracking
- Study progress tracking + per-subject reset
- Topic count fix: `len(MATH_SECTIONS_FALLBACK)` dynamic

### English 七年级上册 ✅
- PDF pipeline processed: 11 sections across 5 chapters
- Keypoints, mindmaps, exercises auto-generated via DeepSeek
- RAG retriever (37 docs) with metadata for structural queries
- Chat modal supports English subject

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
- Per-subject error book and reset

### Code Quality (Post-Review)
- ✅ XSS fixes: `html.escape()` all user input
- ✅ Session isolation by subject
- ✅ Retriever: asyncio.Lock, instance-level paths, keyword fallback
- ✅ Catalog: asyncio.Lock for concurrent mutations
- ✅ CSS deduplication (removed 77-line inline block from base.html)
- ✅ Shared constants in config.py (SUBJECT_NAMES/ICONS/DESCRIPTIONS)
- ✅ AITutorService singleton via `get_ai_tutor()`
- ✅ Pipeline-specific exceptions, import safety, logging

## Key Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI entry, static mounts, lifespan |
| `config.py` | Settings + shared constants |
| `routes/pages.py` | Home, subject, lesson, mindmap, dynamic catalog |
| `routes/chat.py` | RAG chat with SSE streaming, per-subject retrievers |
| `routes/exercises.py` | Exercises, Word download, error book, reset |
| `routes/admin.py` | Pipeline management, upload, delete |
| `services/retriever.py` | TF-IDF + keyword fallback, instance-level paths |
| `services/ai_tutor.py` | DeepSeek API wrapper + singleton |
| `services/pipeline.py` | PDF→knowledge-point automated pipeline |
| `services/progress.py` | Study progress tracking |
| `templates/base.html` | Base layout (clean, no inline CSS) |
| `templates/home.html` | Hero + subject cards + chat modal |
| `templates/admin.html` | Two-column admin with drag-drop |
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
# Admin: http://localhost:8000/admin
```

## Next Steps

1. Add more exercise data for English sections (currently AI-generated, could use review)
2. Chinese (语文) PDF processing
3. Consider upgrading to ONNX Chinese embedding model for better semantic search
4. Mobile responsive refinements
