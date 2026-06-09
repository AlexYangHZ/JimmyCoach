"""Page routes — serve HTML pages."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.curriculum import CurriculumService
from services.progress import ProgressService
from config import settings

router = APIRouter()

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

    last_session = await progress_svc.get_last_session()
    if last_session and not last_session.completed:
        for subj in SUBJECTS_CONFIG:
            topics = curriculum_service.get_topics(grade=subj["grade"], subject=subj["id"])
            topic = curriculum_service.get_topic_by_id(topics, last_session.topic_id)
            if topic:
                suggested_topic = {**topic, "subject": subj["id"], "grade": subj["grade"]}
                break

    return request.app.state.templates.TemplateResponse(
        "home.html",
        {"request": request, "subjects": enriched_subjects, "suggested_topic": suggested_topic},
    )


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
        },
    )
