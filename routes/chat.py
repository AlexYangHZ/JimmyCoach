"""Chat routes — RAG-based subject Q&A using DeepSeek."""

import html as _html
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.ai_tutor import AITutorService
from services.progress import ProgressService
from services.retriever import get_retriever as _get_retriever_async
from config import settings

router = APIRouter()

ai_tutor = AITutorService(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    model=settings.deepseek_model,
    prompts_dir=settings.prompts_dir,
)

# Map subjects to their retriever
SUBJECT_RETRIEVERS = {
    "math": _get_retriever_async,
}

RAG_SYSTEM_PROMPT = """你是一位耐心、鼓励性的AI辅导老师，名叫小教练。
你的学生叫Jimmy，今年12岁，正在学习七年级上册的内容。

教学原则：
- 用简单易懂的语言解释概念
- 多用生活中的例子帮助理解
- 每次回复控制在300字以内
- 学生做对时真诚表扬，做错时温和鼓励
- 使用适合12岁学生的语言

重要：回答问题时，请基于下面提供的教材内容进行回答。
如果教材内容不足以回答该问题，请诚实地告诉学生，并基于你的知识补充说明。

教材参考内容：
{context}

请基于以上教材内容回答Jimmy的问题。引用教材中的例子和解释。"""


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
    if subject in SUBJECT_RETRIEVERS:
        retriever_fn = SUBJECT_RETRIEVERS.get(subject)
        if retriever_fn:
            try:
                retriever = await retriever_fn()
                results = retriever.search(message, top_k=3)
                if results:
                    context_chunks = [r["text"][:600] for r in results]
                    rag_source_chapter = results[0]["chapter"]
                    rag_source_section = results[0]["section"]
            except Exception:
                pass

    # Build context
    if context_chunks:
        context_text = "\n\n---\n\n".join(context_chunks)
    else:
        context_text = "（暂无相关教材内容，请基于你的知识回答）"

    system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text)

    # Get AI response
    try:
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
    """Return recent chat messages as HTML partial."""
    progress_svc = ProgressService(db)
    last_session = await progress_svc.get_last_session()
    if not last_session:
        return HTMLResponse('<div class="chat-float-msg assistant">👋 你好！我是小教练，关于七年级上册数学的任何问题都可以问我。</div>')

    history = await progress_svc.get_chat_history(last_session.id)
    if not history:
        return HTMLResponse('<div class="chat-float-msg assistant">👋 你好！有任何关于数学的问题都可以问我。</div>')

    html_parts = []
    for msg in history[-20:]:
        if msg["role"] == "user":
            html_parts.append(f'<div class="chat-float-msg user"><strong>🧑 你：</strong>{_html.escape(msg["content"])}</div>')
        else:
            html_parts.append(f'<div class="chat-float-msg assistant"><strong>🤖 小教练：</strong>{_html.escape(msg["content"])}</div>')

    return HTMLResponse("".join(html_parts))
