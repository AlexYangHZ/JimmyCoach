"""Chat routes — chat messaging and history."""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.ai_tutor import AITutorService
from services.progress import ProgressService
from services.chat_context import ChatContextService, LessonContext
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


@router.post("/chat/send", response_class=HTMLResponse)
async def chat_send(
    request: Request,
    message: str = Form(...),
    topic_id: str = Form(""),
    subject: str = Form(""),
    grade: int = Form(6),
    db: AsyncSession = Depends(get_db),
):
    """Send a chat message and get AI response as HTML partial."""
    progress_svc = ProgressService(db)

    ctx = LessonContext()
    if topic_id and subject:
        topics = curriculum_service.get_topics(grade=grade, subject=subject)
        topic = curriculum_service.get_topic_by_id(topics, topic_id)
        topic_meta = curriculum_service.get_topic_meta(grade=grade, subject=subject, topic_id=topic_id)
        ctx = ChatContextService.make_lesson_context(topic, topic_meta, grade, subject)

    last_session = await progress_svc.get_last_session()
    session_id = last_session.id if last_session else None
    if not session_id:
        session_id = await progress_svc.start_session(topic_id or "free-chat")

    chat_history = await progress_svc.get_chat_history(session_id)

    context_dict = ChatContextService.context_for_chat(ctx)
    messages = ai_tutor.build_chat_messages(
        user_message=message,
        chat_history=chat_history,
        topic_context=context_dict,
    )

    await progress_svc.add_chat_message(session_id, "user", message)

    try:
        response = await ai_tutor.client.chat.completions.create(
            model=ai_tutor.model,
            messages=messages,
            temperature=0.8,
            max_tokens=300,
            stream=False,
        )
        reply = response.choices[0].message.content or "..."
    except Exception:
        reply = "😔 老师有点忙，请稍后再试。"

    await progress_svc.add_chat_message(session_id, "assistant", reply)

    return HTMLResponse(
        f'<div class="chat-msg msg-user">'
        f'<span class="msg-avatar">🧑</span>'
        f'<span class="msg-content">{message}</span>'
        f'</div>'
        f'<div class="chat-msg msg-assistant">'
        f'<span class="msg-avatar">🤖</span>'
        f'<span class="msg-content">{reply}</span>'
        f'</div>'
    )


@router.get("/chat", response_class=HTMLResponse)
async def free_chat_page(request: Request):
    """Standalone free chat page."""
    return request.app.state.templates.TemplateResponse("free_chat.html", {"request": request})


@router.get("/chat/history", response_class=HTMLResponse)
async def chat_history(
    topic: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Return recent chat messages as HTML partial."""
    progress_svc = ProgressService(db)
    last_session = await progress_svc.get_last_session()
    if not last_session:
        return HTMLResponse('<div class="chat-empty"><p>👋 你好！有什么问题尽管问我。</p></div>')

    history = await progress_svc.get_chat_history(last_session.id)
    if not history:
        return HTMLResponse('<div class="chat-empty"><p>👋 你好！有什么问题尽管问我。</p></div>')

    html_parts = []
    for msg in history[-20:]:
        role_class = "msg-assistant" if msg["role"] == "assistant" else "msg-user"
        avatar = "🤖" if msg["role"] == "assistant" else "🧑"
        html_parts.append(
            f'<div class="chat-msg {role_class}">'
            f'<span class="msg-avatar">{avatar}</span>'
            f'<span class="msg-content">{msg["content"]}</span>'
            f'</div>'
        )

    return HTMLResponse("".join(html_parts))
