# JimmyCoach — Current Status (2026-06-09)

## What's Built

### Core
- **FastAPI** app with Jinja2 + Htmx + SQLite
- **DeepSeek API** integration for AI chat & exercise grading
- **29 tests** passing

### Math 七年级上册 (Ready ✅)
- PDF split into **17 section PDFs** (one per knowledge point)
- **Mind maps** for all 17 sections (interactive tree, save as PNG)
- **Exercises** — pre-built with click-to-reveal answers (2 sections filled, others use default)
- **Word download** (.docx) for printable worksheets
- **RAG chat** — jieba + TF-IDF retrieval over textbook, DeepSeek answers with source attribution
- **Floating chat widget** — collapsible, bottom-right, on all pages
- **PDF viewer** — iframe + top-right link to full textbook PDF
- Home page shows math card with PDF link, English/Chinese show "coming soon"

### English & Chinese 七年级上册 (Not Started ⏳)
- PDF files present in `docs/`
- No extraction/processing pipeline yet

## Key Files

| File | Purpose |
|---|---|
| `main.py` | App entry, static mounts, lifespan |
| `routes/pages.py` | Home, subject, lesson, mindmap routes |
| `routes/chat.py` | RAG chat with DeepSeek |
| `routes/exercises.py` | Exercise display, Word download |
| `services/retriever.py` | jieba+TF-IDF search engine |
| `services/ai_tutor.py` | DeepSeek API wrapper |
| `data/textbooks/math/grade7/pages/` | 17 section PDFs + full PDF |
| `data/mindmaps/math_grade7.py` | Mind map tree data |
| `scripts/extract_math.py` | PDF→Markdown extraction |
| `scripts/split_pdf.py` | PDF→per-section PDFs |

## How to Run

```bash
cd ~/projects/JimmyCoach
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
# Open http://localhost:8000
```

## Next Steps (Tomorrow)

1. 英语 PDF → extract → split → mind maps → exercises
2. 语文 PDF → extract → split → mind maps → exercises  
3. Fill in remaining exercise data for math sections
4. Consider embedding model upgrade (currently TF-IDF, could use BGE/m3e for better Chinese retrieval)
