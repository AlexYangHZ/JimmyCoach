"""Admin routes for PDF pipeline management."""

import json, shutil, asyncio
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from db.database import get_db
from db.models import PipelineTask
from services.pipeline import get_pipeline
from routes.pages import get_nav_subjects, SUBJECT_CATALOG

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/admin")


@router.get("", response_class=HTMLResponse)
async def admin_page(request: Request):
    return request.app.state.templates.TemplateResponse(
        "admin.html", {"request": request, "nav_subjects": get_nav_subjects()})


@router.post("/upload")
async def admin_upload(
    request: Request,
    file: UploadFile = File(...),
    subject: str = Form(...),
    subject_name: str = Form(...),
    grade: int = Form(...),
    semester: str = Form("上册"),
    db: AsyncSession = Depends(get_db),
):
    safe_name = f"{subject}_grade{grade}_{semester}.pdf"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        f.write(await file.read())

    task = PipelineTask(
        subject=subject, subject_name=subject_name,
        grade=grade, semester=semester, pdf_path=str(file_path),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    pipeline = get_pipeline(db)
    try:
        await pipeline.phase1_extract(task.id)
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)[:500]
        await db.commit()

    return await admin_page(request)


@router.get("/tasks", response_class=HTMLResponse)
async def list_tasks(db: AsyncSession = Depends(get_db)):
    stmt = select(PipelineTask).order_by(PipelineTask.created_at.desc()).limit(20)
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    if not tasks:
        return HTMLResponse('<p style="color:var(--text-light);text-align:center;padding:20px">暂无处理任务</p>')

    status_map = {
        "pending": ("⏳", "等待处理"), "phase1": ("🔍", "正在分析目录..."),
        "awaiting_confirm": ("👆", "请确认章节结构"),
        "phase2": ("🔄", "正在生成内容"), "phase3": ("📦", "正在发布..."),
        "done": ("✅", "已完成"), "failed": ("❌", "处理失败"),
    }

    html = ['<div class="task-list">']
    for t in tasks:
        icon, label = status_map.get(t.status, ("❓", t.status))
        bar = ""
        if t.status in ("phase2", "phase3"):
            bar = f'<div class="task-progress"><div class="task-progress-fill" style="width:{t.progress}%"></div></div>'

        actions = ""
        if t.status == "awaiting_confirm" and t.chapters_json:
            actions = f'<button class="btn-start" onclick="showConfirm({t.id})" style="font-size:.85rem;margin-top:8px">确认章节</button>'
        elif t.status == "done":
            actions = f'<a href="/subjects/{t.subject}/{t.grade}" class="btn-start" style="font-size:.85rem;margin-top:8px">查看</a>'
        elif t.status == "failed":
            actions = f'<button class="btn-reset" onclick="retryTask({t.id})" style="font-size:.85rem;margin-top:8px">重试</button>'

        err = f'<p class="task-err">{t.error_message[:200]}</p>' if t.error_message else ""

        html.append(
            f'<div class="task-card">'
            f'<div class="task-card-top"><span class="task-icon">{icon}</span>'
            f'<span class="task-name">{t.subject_name} {t.grade}年级{t.semester}</span>'
            f'<span class="task-status">{label} {t.progress}%</span></div>'
            f'{bar}{err}{actions}'
            f'</div>'
        )
    html.append('</div>')
    return HTMLResponse("".join(html))


@router.post("/confirm/{task_id}")
async def confirm_chapters(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(PipelineTask, task_id)
    if not task or not task.chapters_json:
        return HTMLResponse("Task not found")

    chapters = json.loads(task.chapters_json)
    pipeline = get_pipeline(db)
    asyncio.create_task(pipeline.phase2_process(task_id, chapters))

    return HTMLResponse('<div style="padding:20px;text-align:center"><h3>✅ 处理已开始</h3><p>请等待任务完成，页面会自动刷新</p></div>')


@router.get("/progress/{task_id}")
async def task_progress(task_id: int, db: AsyncSession = Depends(get_db)):
    async def stream():
        while True:
            task = await db.get(PipelineTask, task_id)
            if not task:
                break
            yield f"data: {json.dumps({'status': task.status, 'progress': task.progress})}\n\n"
            if task.status in ("done", "failed"):
                break
            await asyncio.sleep(2)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/delete/{subject}/{grade}")
async def delete_content(subject: str, grade: int, db: AsyncSession = Depends(get_db)):
    base = Path(f"data/textbooks/{subject}/grade{grade}")
    if base.exists():
        shutil.rmtree(base)
    for prefix in ["keypoints", "mindmaps"]:
        p = Path(f"data/{prefix}/{subject}_grade{grade}.json")
        if p.exists():
            p.unlink()
    ex_file = Path(f"data/exercises/{subject}.json")
    if ex_file.exists():
        ex_file.unlink()
    vec_dir = Path(f"data/vectordb/{subject}")
    if vec_dir.exists():
        shutil.rmtree(vec_dir)

    for subj in SUBJECT_CATALOG:
        subj["grades"] = [g for g in subj["grades"]
                          if not (g["grade"] == grade and g.get("ready"))]

    # Also clean up tasks
    await db.execute(delete(PipelineTask).where(
        PipelineTask.subject == subject, PipelineTask.grade == grade))
    await db.commit()

    return HTMLResponse('<script>location.reload()</script>')


@router.get("/chapters/{task_id}", response_class=HTMLResponse)
async def get_chapters(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(PipelineTask, task_id)
    if not task or not task.chapters_json:
        return HTMLResponse("No chapters found")

    chapters = json.loads(task.chapters_json)
    html = [
        '<div class="confirm-chapters"><h3>📋 确认章节结构</h3>',
        f'<p style="color:var(--text-light);margin-bottom:12px">{task.subject_name} {task.grade}年级{task.semester}</p>',
    ]
    for ch in chapters.get("chapters", []):
        html.append(
            f'<div class="confirm-ch"><strong>第{ch["num"]}章 {ch["title"]}</strong> '
            f'(起始页: {ch.get("start_page", "?")})'
        )
        for s in ch.get("sections", []):
            html.append(f'<div class="confirm-sec">📖 {ch["num"]}.{s["num"]} {s["title"]} (p{s.get("start_page", "?")})</div>')
        html.append('</div>')
    html.append(
        f'<div style="margin-top:16px">'
        f'<button class="btn-start" onclick="confirmChapters({task_id})">✅ 确认，开始处理</button>'
        f'<button class="btn-reset" onclick="document.querySelector(\'.confirm-chapters\').remove()">取消</button>'
        f'</div></div>'
    )
    return HTMLResponse("".join(html))
