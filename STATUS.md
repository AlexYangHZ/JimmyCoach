# JimmyCoach — Current Status (2026-06-10)

## What's Built

### Math 七年级上册 ✅
- PDF split into 17 section PDFs, browser-native iframe viewer
- Mind maps for all 17 sections (interactive tree, save as PNG)
- Key formulas/concepts/tips displayed prominently per knowledge point
- 85 pre-built exercises across all sections (choice, fill-in, true/false)
- All-exercises page with quick-jump nav, interactive answer checking
- Word (.docx) download for printable worksheets
- RAG chat — jieba + TF-IDF retrieval, DeepSeek with source attribution
- Floating chat widget (collapsible, bottom-right)
- Error book with interactive answer mode, error counts
- Study progress tracking (per-topic status, session history)
- Reset button to clear all progress/errors
- 28 tests passing

### English & Chinese 七年级上册 ⏳
- PDF files in `docs/`, not yet processed

## Key Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI entry, static mounts, lifespan |
| `routes/pages.py` | Home, subject, lesson, mindmap |
| `routes/chat.py` | RAG chat with DeepSeek |
| `routes/exercises.py` | Exercises, Word download, error book, reset |
| `services/retriever.py` | jieba+TF-IDF search (lazy sklearn import) |
| `services/ai_tutor.py` | DeepSeek API wrapper |
| `templates/base.html` | Base layout + inline critical CSS |
| `templates/subject.html` | Subject page with chapter blocks |
| `templates/lesson.html` | Lesson page with keypoints + mindmap + exercises |
| `templates/all_exercises.html` | All 85 exercises page (Jinja2 template) |
| `templates/error_book.html` | Error book with answer mode |
| `data/exercises/exercises.json` | 85 exercises in JSON |
| `data/keypoints/math_grade7.py` | Key formulas/concepts/tips |
| `data/mindmaps/math_grade7.py` | Mind map tree data |
| `data/textbooks/math/grade7/pages/` | 17 section PDFs + full PDF |
| `scripts/extract_math.py` | PDF→Markdown extraction |
| `scripts/split_pdf.py` | PDF→per-section PDFs |

## How to Run

```bash
cd ~/projects/JimmyCoach
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
# Open http://localhost:8000
```

## Next Steps

1. 英语/语文 PDF extraction pipeline
2. Upgrade to ChromaDB ONNX embeddings (model already downloaded, dim=384)
3. More exercise data for remaining math sections (reading/history activities)
