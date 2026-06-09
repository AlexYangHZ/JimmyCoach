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
        response = await ai_tutor.client.chat.completions.create(
            model=ai_tutor.model,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
            stream=False,
        )
        content = response.choices[0].message.content or "课程内容生成中..."

        html_paragraphs = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("**") or line.startswith("#"):
                html_paragraphs.append(f'<h3 class="lesson-heading">{line.lstrip("#* ")}</h3>')
            else:
                html_paragraphs.append(f"<p>{line}</p>")

        return HTMLResponse("".join(html_paragraphs))

    except Exception:
        return HTMLResponse('<div class="error">😔 课程内容生成失败，请检查网络连接后重试。</div>')


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
                letter = chr(65 + i)
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

    result = await ai_tutor.grade_answer(
        exercise=exercise,
        student_answer=answer,
        topic_context=topic_id,
    )

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
