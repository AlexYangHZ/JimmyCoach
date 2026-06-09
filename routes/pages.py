"""Page routes — serve HTML pages."""

import yaml
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.progress import ProgressService
from config import settings

router = APIRouter()

# Subject config — 七年级上册, three subjects
SUBJECTS_CONFIG = [
    {"id": "math", "name": "数学", "icon": "📐", "grade": 7, "semester": "上册",
     "description": "有理数、代数式、整式加减、一元一次方程、几何图形初步"},
    {"id": "english", "name": "英语", "icon": "🌐", "grade": 7, "semester": "上册",
     "description": "待添加PDF处理后启用"},
    {"id": "chinese", "name": "语文", "icon": "📖", "grade": 7, "semester": "上册",
     "description": "待添加PDF处理后启用"},
]


def load_math_topics():
    """Load math topics from the extracted textbook index."""
    index_path = settings.data_dir / "textbooks" / "math" / "grade7" / "INDEX.md"
    if not index_path.exists():
        return []

    topics = []
    text = index_path.read_text(encoding="utf-8")
    current_chapter = None

    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## 第") and "章" in line:
            current_chapter = line.lstrip("# ").strip()
        elif line.startswith("- [") and "章" not in line:
            # Parse section: "  - [1.1 正数和负数](chapter_01/section_01.md)"
            import re
            match = re.match(r"- \[([\d.]+)\s+(.+?)\]\((.+?)\)", line)
            if match and current_chapter:
                topics.append({
                    "id": match.group(3).replace("/", "-").replace(".md", ""),
                    "code": match.group(1),
                    "title": match.group(2),
                    "path": match.group(3),
                    "chapter": current_chapter,
                })

    return topics


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    progress_svc = ProgressService(db)

    enriched_subjects = []
    for subj in SUBJECTS_CONFIG:
        # Count topics for math
        topic_count = 0
        if subj["id"] == "math":
            topics = load_math_topics()
            topic_count = len(topics)

        enriched_subjects.append({
            **subj,
            "topic_count": topic_count,
            "ready": subj["id"] == "math",  # Only math is ready
        })

    return request.app.state.templates.TemplateResponse(
        "home.html",
        {"request": request, "subjects": enriched_subjects},
    )


@router.get("/subjects/{subject}/{grade}", response_class=HTMLResponse)
async def subject_page(
    request: Request,
    subject: str,
    grade: int,
    db: AsyncSession = Depends(get_db),
):
    if subject != "math":
        return request.app.state.templates.TemplateResponse(
            "subject.html",
            {
                "request": request,
                "subject": subject,
                "grade": grade,
                "subject_name": {"math": "数学", "english": "英语", "chinese": "语文"}.get(subject, subject),
                "subject_icon": {"math": "📐", "english": "🌐", "chinese": "📖"}.get(subject, "📚"),
                "topics": [],
                "not_ready": True,
            },
        )

    progress_svc = ProgressService(db)
    raw_topics = load_math_topics()

    # Enrich with progress
    simplified = [{"id": t["id"], "title": t["title"], "chapter": t["chapter"],
                    "code": t["code"], "order": i + 1, "dependencies": [], "key_points": []}
                 for i, t in enumerate(raw_topics)]
    enriched = await progress_svc.get_progress_summary(simplified)

    # All topics are available (no hard dependency chain for textbook browsing)
    completed_ids = {t["id"] for t in enriched if t["status"] == "mastered"}
    for topic in enriched:
        topic["available"] = True
        topic["code"] = topic.get("code", "")
        topic["chapter"] = topic.get("chapter", "")

    return request.app.state.templates.TemplateResponse(
        "subject.html",
        {
            "request": request,
            "subject": subject,
            "grade": grade,
            "subject_name": "数学",
            "subject_icon": "📐",
            "topics": enriched,
            "not_ready": False,
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
    """Lesson page with textbook content + exercises + chat."""
    if subject != "math":
        return HTMLResponse("Coming soon", status_code=404)

    # Load markdown content for this topic
    topics = load_math_topics()
    topic = None
    for t in topics:
        if t["id"] == topic_id:
            topic = t
            break

    if not topic:
        return HTMLResponse("Topic not found", status_code=404)

    # Load the actual markdown content
    md_path = settings.data_dir / "textbooks" / "math" / "grade7" / topic["path"]
    content_html = ""
    if md_path.exists():
        md_text = md_path.read_text(encoding="utf-8")
        # Simple markdown to HTML
        html_lines = []
        for line in md_text.split("\n"):
            line = line.strip()
            if not line:
                html_lines.append("<br>")
            elif line.startswith("# "):
                html_lines.append(f'<h2>{line[2:]}</h2>')
            elif line.startswith("## "):
                html_lines.append(f'<h3>{line[3:]}</h3>')
            elif line.startswith("**"):
                html_lines.append(f'<p><strong>{line.strip("*")}</strong></p>')
            else:
                html_lines.append(f"<p>{line}</p>")
        content_html = "\n".join(html_lines)

    # Start session
    progress_svc = ProgressService(db)
    session_id = await progress_svc.start_session(topic_id)

    return request.app.state.templates.TemplateResponse(
        "lesson.html",
        {
            "request": request,
            "subject": subject,
            "grade": grade,
            "topic": topic,
            "session_id": session_id,
            "subject_name": "数学",
            "content_html": content_html,
        },
    )
