# Pipeline & Admin Backend — Design Spec

**Date:** 2026-06-11  
**Topic:** Automated PDF-to-knowledge-point pipeline with management backend

## Overview

Abstract the manual textbook processing into an automated pipeline: upload a PDF, fill in basic metadata (subject, grade, semester), confirm detected chapter structure, and the system automatically completes all processing — PDF splitting, AI content generation, vector indexing, and publishing to the frontend.

## Core Decisions

| Decision | Choice |
|---|---|
| **Automation level** | Full automation with chapter confirmation gate |
| **Backend location** | Embedded `/admin` route in existing FastAPI app |
| **Access control** | No login (local single-user) |
| **Progress tracking** | SSE (Server-Sent Events) for real-time progress |
| **AI engine** | DeepSeek API (existing integration) |
| **PDF processing** | PyMuPDF (existing) |

## Architecture

```
JimmyCoach FastAPI App
├── /                     Student frontend (existing)
├── /admin                Management backend (new)
│   ├── GET  /admin            Admin page (upload + task list)
│   ├── POST /admin/upload     Upload PDF + create task
│   ├── GET  /admin/tasks      List all tasks
│   ├── POST /admin/confirm    Confirm chapter structure
│   ├── GET  /admin/progress   SSE progress stream
│   └── POST /admin/delete     Delete published content
├── routes/admin.py       (new)
├── services/pipeline.py  (new)
└── db/models.py          + PipelineTask table
```

No new dependencies. No new frameworks. Same FastAPI process, same SQLite, same DeepSeek client.

## Pipeline Phases

### Phase 1: Structure Extraction (10s)
1. PyMuPDF extracts all text from uploaded PDF
2. Extract the table-of-contents pages
3. DeepSeek parses TOC text → structured chapter/section JSON
4. Return chapter list to user for confirmation (with page ranges)

### Phase 2: Full Processing (2-5 min, background task)
For each confirmed section:
1. PyMuPDF splits PDF into per-section files → `data/textbooks/{subject}/grade{n}/pages/`
2. DeepSeek generates key concepts/formulas/tips → `data/keypoints/{subject}_grade{n}.py`
3. DeepSeek generates mind map tree structure → `data/mindmaps/{subject}_grade{n}.py`
4. DeepSeek generates 5 exercises (choice/fill/true_false) → `data/exercises/{subject}.json`
5. Build TF-IDF retriever index → `data/vectordb/{subject}/`

Progress pushed to frontend via SSE (`/admin/progress?task_id=xxx`).

### Phase 3: Publish
1. Write all generated data files
2. Register subject in `SUBJECT_CATALOG` (append to catalog)
3. Frontend immediately reflects new subject on home page

## Data Model

### PipelineTask (new SQLite table)
```python
class PipelineTask(Base):
    __tablename__ = "pipeline_tasks"
    id = Column(Integer, primary_key=True)
    subject = Column(String(50))       # "math", "english", "chinese"
    subject_name = Column(String(50))  # "数学", "英语", "语文"
    grade = Column(Integer)
    semester = Column(String(10))      # "上册", "下册"
    pdf_path = Column(String(500))     # stored PDF location
    status = Column(String(20))        # pending/phase1/awaiting_confirm/phase2/phase3/done/failed
    progress = Column(Integer, default=0)  # 0-100
    chapters_json = Column(Text)       # detected chapter structure (JSON)
    error_message = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

## Admin UI

### Layout
- **Upload area** (top): file input + subject/grade/semester dropdowns + submit button
- **Task list** (middle): card per task showing status, progress bar, action buttons
- **Published content** (bottom): list of ready subjects with view/delete

### Task Status Display
| Status | Display |
|---|---|
| `pending` | ⏳ 等待处理 |
| `phase1` | 🔍 正在分析目录结构... |
| `awaiting_confirm` | 👆 请确认章节结构 |
| `phase2` | 🔄 正在生成内容 ████░░ 67% |
| `phase3` | 📦 正在发布... |
| `done` | ✅ 已完成 · 17知识点 |
| `failed` | ❌ 处理失败 [查看错误] |

### Chapter Confirmation UI
After Phase 1, show a table where user can:
- View detected chapters and sections with page ranges
- Edit section titles
- Add/remove sections
- Confirm to start Phase 2

## Frontend Integration

After pipeline completes, the processed subject automatically appears on the home page via `SUBJECT_CATALOG` update. The catalog becomes dynamic — subjects with `ready=True` grades link to working content pages.

Existing math content is grandfathered in — marked as ready in the catalog, no re-processing needed.

## File Structure (new)

```
routes/admin.py           # Admin routes + upload handler
services/pipeline.py      # Pipeline orchestrator + DeepSeek prompts
db/models.py              # + PipelineTask
templates/admin.html      # Admin page (upload + task list + published)
```

## Error Handling

- PDF extraction failure → task marked `failed` with error message
- DeepSeek API error → retry 3 times, then mark failed
- User cancels mid-processing → delete partial files, mark cancelled
- Duplicate subject+grade+semester → warning, confirm overwrite

## Out of Scope

- Multi-file batch upload
- Editing published content through admin (use file system)
- PDF OCR for scanned textbooks (assumes digital-born PDFs)
- Notification when task completes (polling or page refresh)
