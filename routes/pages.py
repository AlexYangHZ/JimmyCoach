"""Page routes — serve HTML pages."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.progress import ProgressService

router = APIRouter()

SUBJECTS_CONFIG = [
    {"id": "math", "name": "数学", "icon": "📐", "grade": 7, "semester": "上册",
     "pdf_url": "/textbook/math/grade7/pages/full.pdf",
     "description": "有理数、代数式、整式加减、一元一次方程、几何图形初步"},
    {"id": "english", "name": "英语", "icon": "🌐", "grade": 7, "semester": "上册",
     "description": "待添加PDF处理后启用"},
    {"id": "chinese", "name": "语文", "icon": "📖", "grade": 7, "semester": "上册",
     "description": "待添加PDF处理后启用"},
]

# Section → PDF mapping (matches split_pdf.py output)
MATH_SECTIONS = [
    {"id": "ch01_sec01", "code": "1.1", "title": "正数和负数", "chapter": "第1章 有理数", "pdf": "ch01_sec01.pdf", "pages": 5},
    {"id": "ch01_sec02", "code": "1.2", "title": "有理数及其大小比较", "chapter": "第1章 有理数", "pdf": "ch01_sec02.pdf", "pages": 14},
    {"id": "ch01_reading", "code": "阅读", "title": "用正负数表示允许偏差", "chapter": "第1章 有理数", "pdf": "ch01_reading.pdf", "pages": 1},
    {"id": "ch01_history", "code": "数学史", "title": "漫漫长路识负数", "chapter": "第1章 有理数", "pdf": "ch01_history.pdf", "pages": 1},
    {"id": "ch02_sec01", "code": "2.1", "title": "有理数的加法与减法", "chapter": "第2章 有理数的运算", "pdf": "ch02_sec01.pdf", "pages": 13},
    {"id": "ch02_sec02", "code": "2.2", "title": "有理数的乘法与除法", "chapter": "第2章 有理数的运算", "pdf": "ch02_sec02.pdf", "pages": 13},
    {"id": "ch02_sec03", "code": "2.3", "title": "有理数的乘方", "chapter": "第2章 有理数的运算", "pdf": "ch02_sec03.pdf", "pages": 8},
    {"id": "ch03_sec01", "code": "3.1", "title": "列代数式表示数量关系", "chapter": "第3章 代数式", "pdf": "ch03_sec01.pdf", "pages": 10},
    {"id": "ch03_sec02", "code": "3.2", "title": "代数式的值", "chapter": "第3章 代数式", "pdf": "ch03_sec02.pdf", "pages": 6},
    {"id": "ch04_sec01", "code": "4.1", "title": "整式", "chapter": "第4章 整式的加减", "pdf": "ch04_sec01.pdf", "pages": 6},
    {"id": "ch04_sec02", "code": "4.2", "title": "整式的加法与减法", "chapter": "第4章 整式的加减", "pdf": "ch04_sec02.pdf", "pages": 12},
    {"id": "ch05_sec01", "code": "5.1", "title": "方程", "chapter": "第5章 一元一次方程", "pdf": "ch05_sec01.pdf", "pages": 9},
    {"id": "ch05_sec02", "code": "5.2", "title": "解一元一次方程", "chapter": "第5章 一元一次方程", "pdf": "ch05_sec02.pdf", "pages": 13},
    {"id": "ch05_sec03", "code": "5.3", "title": "实际问题与一元一次方程", "chapter": "第5章 一元一次方程", "pdf": "ch05_sec03.pdf", "pages": 12},
    {"id": "ch06_sec01", "code": "6.1", "title": "几何图形", "chapter": "第6章 几何图形初步", "pdf": "ch06_sec01.pdf", "pages": 12},
    {"id": "ch06_sec02", "code": "6.2", "title": "直线、射线、线段", "chapter": "第6章 几何图形初步", "pdf": "ch06_sec02.pdf", "pages": 8},
    {"id": "ch06_sec03", "code": "6.3", "title": "角", "chapter": "第6章 几何图形初步", "pdf": "ch06_sec03.pdf", "pages": 14},
]


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    subjects = []
    for subj in SUBJECTS_CONFIG:
        ready = subj["id"] == "math"
        topic_count = len(MATH_SECTIONS) if ready else 0
        subjects.append({**subj, "topic_count": topic_count, "ready": ready})

    return request.app.state.templates.TemplateResponse(
        "home.html", {"request": request, "subjects": subjects},
    )


@router.get("/subjects/{subject}/{grade}", response_class=HTMLResponse)
async def subject_page(request: Request, subject: str, grade: int,
                        db: AsyncSession = Depends(get_db)):
    if subject != "math":
        name = {"english": "英语", "chinese": "语文"}.get(subject, subject)
        icon = {"english": "🌐", "chinese": "📖"}.get(subject, "📚")
        return request.app.state.templates.TemplateResponse(
            "subject.html", {"request": request, "subject_name": name,
                             "subject_icon": icon, "grade": grade,
                             "topics": [], "not_ready": True})

    progress_svc = ProgressService(db)
    simplified = [{"id": s["id"], "title": s["title"], "chapter": s["chapter"],
                    "code": s["code"], "pages": s["pages"], "order": i + 1,
                    "dependencies": [], "key_points": []}
                  for i, s in enumerate(MATH_SECTIONS)]
    enriched = await progress_svc.get_progress_summary(simplified)
    for t in enriched:
        t["available"] = True

    return request.app.state.templates.TemplateResponse(
        "subject.html", {"request": request, "subject": subject, "grade": grade,
                         "subject_name": "数学", "subject_icon": "📐",
                         "topics": enriched, "not_ready": False})


@router.get("/learn/{subject}/{grade}/{topic_id}", response_class=HTMLResponse)
async def lesson_page(request: Request, subject: str, grade: int, topic_id: str,
                       db: AsyncSession = Depends(get_db)):
    if subject != "math":
        return HTMLResponse("Coming soon", status_code=404)

    sec = None
    for s in MATH_SECTIONS:
        if s["id"] == topic_id:
            sec = s
            break
    if not sec:
        return HTMLResponse("Not found", status_code=404)

    pdf_url = f"/textbook/math/grade7/pages/{sec['pdf']}"
    progress_svc = ProgressService(db)
    session_id = await progress_svc.start_session(topic_id)

    return request.app.state.templates.TemplateResponse(
        "lesson.html", {
            "request": request, "subject": subject, "grade": grade,
            "section": sec, "pdf_url": pdf_url, "session_id": session_id,
            "subject_name": "数学",
        })
