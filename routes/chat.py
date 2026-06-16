"""Chat routes — unified RAG Q&A with multi-subject retrieval and streaming."""

import html as _html
import json
from pathlib import Path

import yaml
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.ai_tutor import get_ai_tutor
from services.progress import ProgressService
from services.retriever import search_all

router = APIRouter()

# Load RAG system prompt from YAML
def _load_rag_prompt() -> str:
    path = Path("prompts/rag_chat.yaml")
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("system", "")
    return "你是小教练，一位耐心的AI辅导老师。基于教材内容回答学生问题。"

RAG_SYSTEM_PROMPT = _load_rag_prompt()

# In-memory conversation history (session_key -> list of {role, content})
_chat_histories: dict[str, list[dict]] = {}
MAX_HISTORY_TURNS = 6


def _get_history(session_key: str) -> list[dict]:
    return _chat_histories.get(session_key, [])


def _add_to_history(session_key: str, role: str, content: str):
    if session_key not in _chat_histories:
        _chat_histories[session_key] = []
    _chat_histories[session_key].append({"role": role, "content": content})
    max_msgs = MAX_HISTORY_TURNS * 2
    if len(_chat_histories[session_key]) > max_msgs:
        _chat_histories[session_key] = _chat_histories[session_key][-max_msgs:]


def _format_history(history: list[dict]) -> str:
    if not history:
        return "（这是对话的开始）"
    lines = []
    for msg in history[-MAX_HISTORY_TURNS * 2:]:
        role_label = "Jimmy" if msg["role"] == "user" else "小教练"
        lines.append(f"{role_label}: {msg['content']}")
    return "\n".join(lines)


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Render the standalone chat page."""
    from routes.pages import _ctx
    ctx = _ctx(request)
    return request.app.state.templates.TemplateResponse("chat.html", ctx)


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    message: str = Form(...),
    subject: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Streaming RAG chat with multi-subject retrieval and conversation history."""
    progress_svc = ProgressService(db)

    retriever_subject = subject if subject else None
    session_key = f"chat:{subject or 'all'}"

    # Save user message
    _add_to_history(session_key, "user", message)

    try:
        session_id = await progress_svc.start_session(f"{subject or 'all'}-chat")
        await progress_svc.add_chat_message(session_id, "user", message)
    except Exception:
        pass

    # === RAG: Multi-subject retrieval ===
    context_text = ""
    source_info = ""
    try:
        results = await search_all(message, subject=retriever_subject, top_k=5, min_score=0.05)
        if results:
            chunks = []
            sources = []
            seen_sources = set()
            for r in results:
                subj_label = r.get("subject", "")
                chunks.append(
                    f"【{subj_label} · {r['chapter']} · {r['section']}】\n{r['text'][:800]}"
                )
                src_key = f"{subj_label} {r['chapter']}"
                if src_key not in seen_sources and len(sources) < 3:
                    sources.append(src_key)
                    seen_sources.add(src_key)

            context_text = "\n\n---\n\n".join(chunks)
            source_info = " · ".join(sources)
    except Exception as e:
        print(f"[RAG] Retrieval error: {e}")

    if not context_text:
        context_text = "（暂无相关教材内容，请基于你的知识回答）"

    # Build prompt
    history_text = _format_history(_get_history(session_key))
    system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text, history=history_text)

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
                temperature=0.3,
                max_tokens=800,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    collected.append(delta.content)
                    yield f"data: {json.dumps({'token': delta.content})}\n\n"

            full_reply = "".join(collected)
            _add_to_history(session_key, "assistant", full_reply)

            try:
                last_session = await progress_svc.get_last_session()
                if last_session:
                    await progress_svc.add_chat_message(last_session.id, "assistant", full_reply)
            except Exception:
                pass

            done_data = {"done": True}
            if source_info:
                done_data["source"] = f"📖 参考：{source_info}"
            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': '😔 老师有点忙，请稍后再试。'})}\n\n"
            print(f"[Chat Stream] Error: {e}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
