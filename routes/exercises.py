"""Exercise routes — serve pre-generated exercises with answer reveal + Word download."""

import json
import io
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, StreamingResponse
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from services.ai_tutor import AITutorService
from services.progress import ProgressService
from config import settings

router = APIRouter()

EXERCISE_CACHE_DIR = Path("data/exercises/math")
EXERCISE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Pre-built exercises for each section (generated once, served fast)
# Format: list of {type, question, choices?, answer, explanation}

EXERCISES = {
    "ch01_sec01": [
        {"type": "choice", "question": "下列哪个是负数？", "choices": ["5", "0", "-3", "1/2"], "answer": 2, "explanation": "负数是小于0的数，-3是负数。"},
        {"type": "choice", "question": "如果上升5m记作+5m，那么下降3m记作什么？", "choices": ["+3m", "-3m", "0m", "3m"], "answer": 1, "explanation": "具有相反意义的量，下降用负数表示，所以是-3m。"},
        {"type": "choice", "question": "0是正数还是负数？", "choices": ["正数", "负数", "既是正数也是负数", "既不是正数也不是负数"], "answer": 3, "explanation": "0既不是正数也不是负数，它是正数和负数的分界点。"},
        {"type": "fill", "question": "比0大5的数是___，比0小3的数是___。", "answer": "+5（或5）, -3", "explanation": "比0大的数是正数，比0小的数是负数。"},
        {"type": "choice", "question": "如果向东走50m记作+50m，那么-30m表示什么？", "choices": ["向东走30m", "向西走30m", "向南走30m", "向北走30m"], "answer": 1, "explanation": "正数表示向东，那么负数表示相反方向即向西。"},
    ],
    "ch01_sec02": [
        {"type": "choice", "question": "下列哪个是有理数？", "choices": ["π", "√2", "-5", "e"], "answer": 2, "explanation": "有理数是可以写成分数形式的数，-5=-5/1是有理数。"},
        {"type": "choice", "question": "在数轴上，-3和2哪个大？", "choices": ["-3大", "2大", "一样大", "无法比较"], "answer": 1, "explanation": "在数轴上右边的数总比左边的大，2在-3的右边。"},
        {"type": "fill", "question": "|-5|的值是___。", "answer": "5", "explanation": "绝对值表示数轴上的点到原点的距离，|-5|=5。"},
        {"type": "choice", "question": "下列各数中，最小的是？", "choices": ["-2", "0", "1", "-5"], "answer": 3, "explanation": "负数中，绝对值大的反而小，|-5|>|-2|，所以-5最小。"},
        {"type": "fill", "question": "比-3大比2小的整数有___个。", "answer": "4（-2, -1, 0, 1）", "explanation": "-2, -1, 0, 1都在-3和2之间。"},
    ],
    "default": [
        {"type": "choice", "question": "请先学习教材内容，再来做练习哦！", "choices": ["知道了"], "answer": 0, "explanation": "这个知识点的练习题正在准备中，先仔细阅读教材吧！"},
    ],
}


def _build_exercise_html(section_id: str) -> str:
    """Build HTML for a set of exercises."""
    ex_list = EXERCISES.get(section_id, EXERCISES["default"])
    if not ex_list:
        ex_list = EXERCISES["default"]

    parts = []
    for i, ex in enumerate(ex_list):
        qid = f"q-{section_id}-{i}"
        parts.append(f'<div class="exercise-item" id="{qid}">')
        parts.append(f'<div class="q-title">第{i+1}题：{ex["question"]}</div>')

        if ex["type"] == "choice" and "choices" in ex:
            parts.append('<div class="q-choices">')
            for j, choice in enumerate(ex["choices"]):
                parts.append(
                    f'<span class="q-choice" onclick="checkChoice(\'{qid}\', {j}, {ex["answer"]}, this)">'
                    f'{chr(65+j)}. {choice}</span>'
                )
            parts.append('</div>')
        elif ex["type"] == "fill":
            parts.append(
                f'<div style="margin:8px 0">'
                f'<input type="text" class="exercise-input" id="{qid}-input" '
                f'placeholder="输入你的答案" style="max-width:300px"> '
                f'<button class="btn-submit" onclick="checkFill(\'{qid}\', \'{ex["answer"]}\')">检查</button>'
                f'</div>'
            )

        parts.append(
            f'<div class="q-answer" id="{qid}-answer">'
            f'<strong>答案：</strong>{ex["answer"]}<br>'
            f'<strong>解释：</strong>{ex["explanation"]}'
            f'</div>'
        )
        parts.append('</div>')

    return "\n".join(parts)


@router.get("/exercises/{section_id}", response_class=HTMLResponse)
async def get_exercises(section_id: str):
    """Return pre-built exercises for a section as HTML."""
    html = _build_exercise_html(section_id)
    # Also include the interactive JS
    js = """
<script>
function checkChoice(qid, selected, correct, el) {
    var choices = document.querySelectorAll('#' + qid + ' .q-choice');
    choices.forEach(function(c) { c.classList.remove('selected', 'correct', 'wrong'); });
    if (selected === correct) {
        el.classList.add('correct');
    } else {
        el.classList.add('wrong');
        choices[correct].classList.add('correct');
    }
    document.getElementById(qid + '-answer').classList.add('show');
}
function checkFill(qid, answer) {
    var input = document.getElementById(qid + '-input');
    var resultDiv = document.getElementById(qid + '-answer');
    if (input.value.trim()) {
        resultDiv.classList.add('show');
    }
}
</script>
"""
    return HTMLResponse(html + js)


@router.get("/exercises/{section_id}/download")
async def download_exercises(section_id: str):
    """Generate and download a Word document of exercises for printing."""
    ex_list = EXERCISES.get(section_id, EXERCISES["default"])
    if not ex_list or ex_list == EXERCISES["default"]:
        # Try to find section name
        from routes.pages import MATH_SECTIONS
        sec_name = section_id
        for s in MATH_SECTIONS:
            if s["id"] == section_id:
                sec_name = f"{s['code']} {s['title']}"
                break
        # Still return a basic doc
        ex_list = [{"type": "choice", "question": "请先学习教材，练习题正在准备中",
                     "choices": ["好的"], "answer": 0, "explanation": ""}]

    doc = Document()

    # Page setup
    style = doc.styles['Normal']
    style.font.name = '宋体'
    style.font.size = Pt(11)
    style.paragraph_format.line_spacing = 1.5

    # Title
    title = doc.add_heading('数学七年级上册 · 练习题', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Subtitle
    from routes.pages import MATH_SECTIONS
    sec_name = section_id
    for s in MATH_SECTIONS:
        if s["id"] == section_id:
            sec_name = f"{s['chapter']} — {s['code']} {s['title']}"
            break
    subtitle = doc.add_paragraph(sec_name)
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].font.size = Pt(12)
    subtitle.runs[0].font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph('姓名：______________    日期：______________    得分：______________')
    doc.add_paragraph('')

    # Exercises
    for i, ex in enumerate(ex_list):
        q_num = f"第{i+1}题"
        q_type_map = {"choice": "【选择题】", "fill": "【填空题】"}
        q_type = q_type_map.get(ex["type"], "【题目】")

        p = doc.add_paragraph()
        run = p.add_run(f"{q_num} {q_type} {ex['question']}")
        run.bold = True
        run.font.size = Pt(11)

        if ex["type"] == "choice" and "choices" in ex:
            for j, choice in enumerate(ex["choices"]):
                doc.add_paragraph(f"    {chr(65+j)}. {choice}", style='List Bullet')

        # Answer space
        doc.add_paragraph('')
        doc.add_paragraph('答：___________________________________________________________')
        doc.add_paragraph('')

    # Answer Key page
    doc.add_page_break()
    ans_title = doc.add_heading('参考答案', level=2)
    ans_title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for i, ex in enumerate(ex_list):
        p = doc.add_paragraph()
        run = p.add_run(f"第{i+1}题答案：{ex.get('answer', '（见解析）')}")
        run.font.size = Pt(10)

        if ex.get("explanation"):
            exp_p = doc.add_paragraph()
            exp_run = exp_p.add_run(f"    解析：{ex['explanation']}")
            exp_run.font.size = Pt(9)
            exp_run.font.color.rgb = RGBColor(100, 100, 100)

    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # Safe ASCII filename for HTTP header
    from urllib.parse import quote
    safe_name = f"math_grade7_exercises_{section_id}.docx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={safe_name}"},
    )
