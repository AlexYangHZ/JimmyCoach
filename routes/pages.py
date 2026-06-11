"""Page routes — serve HTML pages."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.progress import ProgressService
from data.mindmaps.math_grade7 import get_mindmap
from data.keypoints.math_grade7 import get_keypoints

router = APIRouter()


def _ctx(request: Request, **extra) -> dict:
    """Common template context for all pages."""
    return {"request": request, "nav_subjects": get_nav_subjects(), **extra}


# Subject catalog — each subject can have multiple grade/semester entries
# ready=True means content is available, ready=False means coming soon
SUBJECT_CATALOG = [
    {
        "id": "math", "name": "数学", "icon": "📐",
        "description": "涵盖数与代数、图形与几何、统计与概率等核心领域",
        "grades": [
            {"grade": 7, "semester": "上册", "ready": True, "pdf_url": "/textbook/math/grade7/pages/full.pdf"},
        ],
    },
    {
        "id": "english", "name": "英语", "icon": "🌐",
        "description": "人教版七年级英语，听说读写全面发展",
        "grades": [
            {"grade": 7, "semester": "上册", "ready": False},
        ],
    },
    {
        "id": "chinese", "name": "语文", "icon": "📖",
        "description": "统编版七年级语文，经典篇目与写作训练",
        "grades": [
            {"grade": 7, "semester": "上册", "ready": False},
        ],
    },
]

# Build nav items (for header) and home display
def get_nav_subjects():
    """Return list of subjects with their primary grade for nav."""
    nav = []
    for subj in SUBJECT_CATALOG:
        primary = subj["grades"][0]
        nav.append({
            "id": subj["id"], "name": subj["name"], "icon": subj["icon"],
            "grade": primary["grade"], "semester": primary["semester"],
        })
    return nav

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
    for subj in SUBJECT_CATALOG:
        grades_display = []
        for g in subj["grades"]:
            if g["ready"]:
                topic_count = len(MATH_SECTIONS) if subj["id"] == "math" else 0
                grades_display.append({
                    **g, "topic_count": topic_count,
                })
            else:
                grades_display.append({**g, "topic_count": 0})
        subjects.append({**subj, "grades": grades_display})

    return request.app.state.templates.TemplateResponse(
        "home.html", _ctx(request, subjects=subjects))


@router.get("/subjects/{subject}/{grade}", response_class=HTMLResponse)
async def subject_page(request: Request, subject: str, grade: int,
                        db: AsyncSession = Depends(get_db)):
    if subject != "math":
        name = {"english": "英语", "chinese": "语文"}.get(subject, subject)
        icon = {"english": "🌐", "chinese": "📖"}.get(subject, "📚")
        return request.app.state.templates.TemplateResponse(
            "subject.html", _ctx(request, subject_name=name, subject_icon=icon,
                                 grade=grade, subject=subject, topics=[], not_ready=True))

    progress_svc = ProgressService(db)
    simplified = []
    for i, s in enumerate(MATH_SECTIONS):
        simplified.append({
            "id": s["id"], "title": s["title"], "chapter": s["chapter"],
            "code": s["code"], "pages": s["pages"], "order": i + 1,
            "dependencies": [], "key_points": [],
        })
    enriched = await progress_svc.get_progress_summary(simplified)
    for t in enriched:
        t["available"] = True

    return request.app.state.templates.TemplateResponse(
        "subject.html", _ctx(request, subject=subject, grade=grade,
                             subject_name="数学", subject_icon="📐",
                             topics=enriched, not_ready=False))


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
    keypoints = get_keypoints(topic_id)
    progress_svc = ProgressService(db)
    session_id = await progress_svc.start_session(topic_id)

    return request.app.state.templates.TemplateResponse(
        "lesson.html", _ctx(request, subject=subject, grade=grade,
                            section=sec, pdf_url=pdf_url, session_id=session_id,
                            subject_name="数学", keypoints=keypoints))


@router.get("/mindmap/{section_id}", response_class=HTMLResponse)
async def mindmap_page(section_id: str):
    """Return interactive mind map HTML for a section."""
    tree = get_mindmap(section_id)
    if not tree:
        return HTMLResponse('<p class="error">该知识点暂无脑图数据</p>')

    html = _render_tree(tree)
    download_btn = """
<div style="text-align:right;margin-bottom:8px;">
    <button onclick="downloadMindmap()" style="padding:6px 16px;background:#fff;color:#764ba2;border:2px solid #764ba2;border-radius:16px;cursor:pointer;font-size:0.85rem;font-weight:600;">
        📥 保存脑图为图片
    </button>
</div>
"""
    css = """
<style>
.mindmap-wrap { background: #fafbfc; border-radius: 16px; padding: 16px 24px 24px; text-align: center; }
.mindmap-container { display: inline-block; text-align: center; padding: 20px; }
.mindmap-root {
    display: inline-flex; flex-direction: column; align-items: center;
    gap: 20px; min-width: 600px;
}
.mindmap-center {
    background: #4a90d9; color: white; padding: 14px 28px;
    border-radius: 24px; font-size: 1.2rem; font-weight: 700;
    box-shadow: 0 4px 12px rgba(74,144,217,0.3);
}
.mindmap-branches {
    display: flex; flex-wrap: wrap; justify-content: center; gap: 16px;
}
.mindmap-branch {
    display: flex; flex-direction: column; align-items: center;
    gap: 8px; min-width: 140px;
}
.mindmap-line { width: 2px; height: 24px; background: #c8d6e5; }
.mindmap-branch-label {
    background: #eef2f7; padding: 8px 14px; border-radius: 12px;
    font-weight: 600; font-size: 0.9rem;
    border: 2px solid transparent;
    white-space: nowrap;
}
.mindmap-leaves {
    display: flex; flex-wrap: wrap; gap: 6px; justify-content: center;
    max-width: 220px;
}
.mindmap-leaf {
    background: white; padding: 4px 10px; border-radius: 8px;
    font-size: 0.8rem; color: #7f8c8d;
    border: 1px solid #e8ecf0; white-space: nowrap;
}
</style>
<script>
function downloadMindmap() {
    var wrap = document.querySelector('.mindmap-wrap');
    // Use canvas to capture the DOM element as image
    var svgData = '<svg xmlns="http://www.w3.org/2000/svg" width="' + wrap.offsetWidth + '" height="' + wrap.offsetHeight + '">' +
        '<foreignObject width="100%" height="100%">' +
        '<div xmlns="http://www.w3.org/1999/xhtml">' + wrap.innerHTML + '</div>' +
        '</foreignObject></svg>';
    var img = new Image();
    var blob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
    var url = URL.createObjectURL(blob);
    img.onload = function() {
        var canvas = document.createElement('canvas');
        canvas.width = wrap.offsetWidth * 2;
        canvas.height = wrap.offsetHeight * 2;
        var ctx = canvas.getContext('2d');
        ctx.scale(2, 2);
        ctx.fillStyle = '#fafbfc';
        ctx.fillRect(0, 0, wrap.offsetWidth, wrap.offsetHeight);
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        var link = document.createElement('a');
        link.download = 'mindmap.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    };
    img.src = url;
}
</script>
"""
    return HTMLResponse(download_btn + '<div class="mindmap-wrap">' + css + '<div class="mindmap-container">' + html + '</div></div>')


def _render_tree(node, is_root=True) -> str:
    """Render a tree node as interactive HTML."""
    if is_root:
        children_html = ""
        if node.get("children"):
            branches = []
            for child in node["children"]:
                branches.append(_render_tree(child, is_root=False))
            children_html = (
                '<div class="mindmap-branches">'
                + "".join(branches)
                + "</div>"
            )
        return (
            '<div class="mindmap-container">'
            '<div class="mindmap-root">'
            f'<div class="mindmap-center">📐 {node["label"]}</div>'
            + (f'<div class="mindmap-line"></div>' if node.get("children") else "") +
            children_html +
            '</div></div>'
        )
    else:
        # Branch node
        leaves_html = ""
        if node.get("children"):
            leaves = []
            for leaf in node["children"]:
                leaves.append(
                    f'<span class="mindmap-leaf">• {leaf["label"]}</span>'
                )
            leaves_html = '<div class="mindmap-leaves">' + "".join(leaves) + "</div>"

        return (
            '<div class="mindmap-branch">'
            f'<div class="mindmap-line"></div>'
            f'<div class="mindmap-branch-label">{node["label"]}</div>'
            + (f'<div class="mindmap-line"></div>' + leaves_html if node.get("children") else "") +
            '</div>'
        )
