"""Chat routes — RAG-based subject Q&A using DeepSeek."""

import html as _html
import json
from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.ai_tutor import get_ai_tutor
from services.progress import ProgressService
from services.retriever import get_retriever as _get_retriever_async
from config import settings

router = APIRouter()

# Map subjects to their retriever (lazy, created on first use)
_subject_retrievers: dict[str, object] = {}

async def _get_subject_retriever(subject: str):
    """Get or create a retriever for a subject."""
    if subject not in _subject_retrievers:
        from services.retriever import MathRetriever
        r = MathRetriever()
        r.MARKDOWN_DIR = Path(f"data/textbooks/{subject}/grade7")
        r.CACHE_PATH = Path(f"data/vectordb/{subject}/retriever.pkl")
        r.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not r.load():
            r.build_index()
            r.save()
        _subject_retrievers[subject] = r
    return _subject_retrievers[subject]

RAG_SYSTEM_PROMPT = """你是小教练，一位耐心的AI辅导老师。学生Jimmy，12岁，七年级。

要求：
- 直接回答问题，不要重复或复述学生的问题
- 用简单易懂的语言，每次300字以内
- 多用生活例子，像朋友聊天一样
- 基于下面教材内容回答，引用原文例子
- 若教材无相关内容，诚实说明并用自己的知识补充

教材内容：
{context}"""


@router.post("/chat/send", response_class=HTMLResponse)
async def chat_send(
    request: Request,
    message: str = Form(...),
    topic_id: str = Form(""),
    subject: str = Form("math"),
    grade: int = Form(7),
    db: AsyncSession = Depends(get_db),
):
    """RAG-based chat: retrieves relevant textbook content, answers via DeepSeek."""
    progress_svc = ProgressService(db)

    # Get or create session (scoped by subject)
    session_id = None
    last_session = await progress_svc.get_last_session()
    if last_session and topic_id:
        session_id = last_session.id
    if not session_id:
        session_id = await progress_svc.start_session(topic_id or f"{subject}-chat")

    await progress_svc.add_chat_message(session_id, "user", message)

    # === RAG: Retrieve relevant content ===
    context_chunks = []
    rag_source_chapter = ""
    rag_source_section = ""
    try:
        retriever = await _get_subject_retriever(subject)
        results = retriever.search(message, top_k=3)
        if results:
            context_chunks = [r["text"][:600] for r in results]
            rag_source_chapter = results[0]["chapter"]
            rag_source_section = results[0]["section"]
    except Exception as e:
        print(f"[RAG] Retriever error for '{message[:30]}...': {e}")

    # Build context
    if context_chunks:
        context_text = "\n\n---\n\n".join(context_chunks)
    else:
        context_text = "（暂无相关教材内容，请基于你的知识回答）"

    system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text)

    # Get AI response
    try:
        ai_tutor = get_ai_tutor()
        response = await ai_tutor.client.chat.completions.create(
            model=ai_tutor.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
            max_tokens=500,
            stream=False,
        )
        reply = response.choices[0].message.content or "..."
    except Exception as e:
        reply = "😔 老师有点忙，请稍后再试。"
        print(f"DeepSeek error: {e}")

    await progress_svc.add_chat_message(session_id, "assistant", reply)

    # Show source info
    source_info = ""
    if rag_source_chapter:
        source_info = f'<div class="rag-source">📖 参考：{rag_source_chapter} · {rag_source_section}</div>'

    return HTMLResponse(
        f'<div class="chat-float-msg user"><strong>🧑 你：</strong>{_html.escape(message)}</div>'
        f'<div class="chat-float-msg assistant"><strong>🤖 小教练：</strong>{_html.escape(reply)}</div>'
        f'{source_info}'
    )


@router.get("/chat/history", response_class=HTMLResponse)
async def chat_history(
    topic: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Return recent chat messages as HTML partial (filtered by topic)."""
    progress_svc = ProgressService(db)
    from sqlalchemy import select
    from db.models import StudySession
    stmt = select(StudySession).where(StudySession.topic_id == topic).order_by(StudySession.id.desc()).limit(1)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return HTMLResponse('<div class="chat-welcome">👋 你好！关于这门课的任何问题都可以问我。</div>')

    history = await progress_svc.get_chat_history(session.id)
    if not history:
        return HTMLResponse('<div class="chat-welcome">👋 你好！有任何问题都可以问我。</div>')

    html_parts = []
    for msg in history[-30:]:
        cls = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-ai"
        html_parts.append(f'<div class="{cls}">{_html.escape(msg["content"])}</div>')

    return HTMLResponse("".join(html_parts))


@router.post("/chat/stream")
async def chat_stream(
    message: str = Form(...),
    subject: str = Form("math"),
    topic_id: str = Form(""),
    grade: int = Form(7),
    db: AsyncSession = Depends(get_db),
):
    """Streaming RAG chat with SSE for typewriter effect."""
    progress_svc = ProgressService(db)

    # Get or create session
    session_id = None
    last_session = await progress_svc.get_last_session()
    if last_session and topic_id:
        session_id = last_session.id
    if not session_id:
        session_id = await progress_svc.start_session(topic_id or f"{subject}-chat")

    await progress_svc.add_chat_message(session_id, "user", message)

    # === RAG retrieval ===
    context_chunks = []
    rag_source_chapter = ""
    try:
        retriever = await _get_subject_retriever(subject)
        results = retriever.search(message, top_k=3)
        if results:
            context_chunks = [r["text"][:600] for r in results]
            rag_source_chapter = results[0]["chapter"]
    except Exception as e:
        print(f"[RAG] Stream error: {e}")

    context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else "（暂无相关教材内容）"
    system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text)

    async def event_stream():
        collected = []
        try:
            ai_tutor = get_ai_tutor()
            stream = await ai_tutor.client.chat.completions.create(
                model=ai_tutor.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=0.7, max_tokens=500, stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    collected.append(delta.content)
                    yield f"data: {json.dumps({'token': delta.content})}\n\n"

            full_reply = "".join(collected)
            await progress_svc.add_chat_message(session_id, "assistant", full_reply)

            source = ""
            if rag_source_chapter:
                source = f"📖 参考：{rag_source_chapter}"
            yield f"data: {json.dumps({'done': True, 'source': source})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': '老师有点忙，请稍后再试'})}\n\n"
            print(f"[Stream] Error: {e}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
