"""Exercise routes — generate exercises via DeepSeek, grade answers."""

from fastapi import APIRouter, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from services.ai_tutor import AITutorService
from services.progress import ProgressService
from services.retriever import get_retriever
from config import settings

router = APIRouter()

ai_tutor = AITutorService(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    model=settings.deepseek_model,
    prompts_dir=settings.prompts_dir,
)

EXERCISE_GEN_PROMPT = """基于以下教材内容，为Jimmy生成3道练习题。

教材内容：
{context}

要求：
1. 题目类型多样化：1道选择题 + 1道填空题 + 1道判断题
2. 难度适合七年级学生
3. 基于教材内容出题，不要超出范围

请按以下格式输出（严格遵循）：

选择题：
题目：[题目内容]
A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]
正确答案：[A/B/C/D]

填空题：
题目：[题目内容]
正确答案：[答案]

判断题：
题目：[题目内容]
正确答案：[正确/错误]"""


@router.get("/learn/{subject}/{grade}/{topic_id}/exercises", response_class=HTMLResponse)
async def load_exercises(
    subject: str,
    grade: int,
    topic_id: str,
):
    """Generate AI exercises based on textbook content."""
    if subject != "math":
        return HTMLResponse('<p>练习题即将上线</p>')

    # Get textbook content for this topic
    parts = topic_id.split("-")
    md_filename = f"{parts[-1]}.md" if len(parts) > 1 else f"{topic_id}.md"

    md_path = settings.data_dir / "textbooks" / "math" / "grade7"
    # Find the markdown file
    md_file = None
    for f in md_path.rglob("*.md"):
        if topic_id in str(f) or (len(parts) > 1 and parts[-1] in str(f.stem)):
            md_file = f
            break

    if not md_file:
        return HTMLResponse('<p>暂无练习题</p>')

    context = md_file.read_text(encoding="utf-8")[:2000]

    # Generate exercises via DeepSeek
    try:
        response = await ai_tutor.client.chat.completions.create(
            model=ai_tutor.model,
            messages=[
                {"role": "system", "content": EXERCISE_GEN_PROMPT.format(context=context)},
            ],
            temperature=0.7,
            max_tokens=500,
            stream=False,
        )
        content = response.choices[0].message.content or ""
    except Exception:
        return HTMLResponse('<p>😔 练习生成失败，请稍后再试。</p>')

    # Parse the generated exercises
    import re

    exercises = []
    current = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("选择题："):
            if current:
                exercises.append(current)
            current = {"type": "multiple_choice", "question": line[4:].strip()}
        elif line.startswith("A. "):
            current.setdefault("options", []).append(line)
        elif line.startswith("B. "):
            current.setdefault("options", []).append(line)
        elif line.startswith("C. "):
            current.setdefault("options", []).append(line)
        elif line.startswith("D. "):
            current.setdefault("options", []).append(line)
        elif line.startswith("正确答案：") and current.get("type") == "multiple_choice":
            current["correct"] = line[5:].strip()
        elif line.startswith("填空题："):
            if current:
                exercises.append(current)
            current = {"type": "fill_blank", "question": line[4:].strip()}
        elif line.startswith("正确答案：") and current.get("type") == "fill_blank":
            current["correct"] = line[5:].strip()
        elif line.startswith("判断题："):
            if current:
                exercises.append(current)
            current = {"type": "true_false", "question": line[4:].strip()}
        elif line.startswith("正确答案：") and current.get("type") == "true_false":
            current["correct"] = line[5:].strip()
    if current:
        exercises.append(current)

    if not exercises:
        return HTMLResponse('<p>暂无练习题</p>')

    # Build HTML
    html_parts = []
    for i, ex in enumerate(exercises):
        ex_id = f"gen-{i}"
        q_type = ex.get("type", "")
        question = ex.get("question", "题目解析失败")

        html_parts.append(f'<div class="exercise-card" id="exercise-{ex_id}">')
        html_parts.append(f'<p class="exercise-question"><strong>{question}</strong></p>')

        if q_type == "multiple_choice":
            html_parts.append('<div class="exercise-options">')
            for opt in ex.get("options", []):
                # Parse letter and text
                opt_match = re.match(r"([A-D])\.\s*(.+)", opt)
                if opt_match:
                    letter, text = opt_match.group(1), opt_match.group(2)
                    html_parts.append(
                        f'<button class="btn-option" '
                        f'hx-post="/exercise/check" '
                        f'hx-vals=\'{{"exercise_id":"{ex_id}","answer":"{letter}","topic_id":"{topic_id}","correct_answer":"{ex.get("correct","")}","question":"{question}"}}\' '
                        f'hx-target="#exercise-{ex_id}" '
                        f'hx-swap="outerHTML">'
                        f'{letter}. {text}</button>'
                    )
            html_parts.append('</div>')
        elif q_type == "fill_blank":
            html_parts.append(
                f'<form hx-post="/exercise/check" hx-target="#exercise-{ex_id}" hx-swap="outerHTML" class="exercise-form">'
                f'<input type="hidden" name="exercise_id" value="{ex_id}">'
                f'<input type="hidden" name="topic_id" value="{topic_id}">'
                f'<input type="hidden" name="correct_answer" value="{ex.get("correct","")}">'
                f'<input type="hidden" name="question" value="{question}">'
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
                    f'hx-vals=\'{{"exercise_id":"{ex_id}","answer":"{ans}","topic_id":"{topic_id}","correct_answer":"{ex.get("correct","")}","question":"{question}"}}\' '
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
    correct_answer: str = Form(""),
    question: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Grade an exercise answer using simple comparison + AI feedback."""
    # Simple match check
    is_correct = None
    if correct_answer:
        # Normalize comparison
        student = answer.strip()
        expected = correct_answer.strip()
        if student == expected:
            is_correct = True
        elif student.upper() == expected.upper():
            is_correct = True
        elif student in expected or expected in student:
            is_correct = None  # Partial — let AI decide
        else:
            is_correct = False

    # Get AI feedback
    try:
        response = await ai_tutor.client.chat.completions.create(
            model=ai_tutor.model,
            messages=[
                {"role": "system", "content": "请评价Jimmy的答案。输出格式：对错: [正确/错误/部分正确]\n反馈: [2-3句话的鼓励性反馈]"},
                {"role": "user", "content": f"题目：{question}\n正确答案：{correct_answer}\nJimmy的答案：{answer}\n\n请评价。"},
            ],
            temperature=0.3,
            max_tokens=200,
            stream=False,
        )
        ai_result = response.choices[0].message.content or ""
    except Exception:
        ai_result = f"对错: {'正确' if is_correct else '错误'}\n反馈: 已收到你的答案！"

    # Parse AI result
    import re
    ai_correct = None
    match = re.search(r"对错:\s*(正确|错误|部分正确)", ai_result)
    if match:
        status = match.group(1)
        if status == "正确":
            ai_correct = True
        elif status == "错误":
            ai_correct = False

    feedback = ""
    fb_match = re.search(r"反馈:\s*(.+)", ai_result, re.DOTALL)
    if fb_match:
        feedback = fb_match.group(1).strip()

    # Fall back to simple comparison if AI parsing fails
    if ai_correct is None:
        ai_correct = is_correct

    if ai_correct is True:
        status_icon, status_class = "✅", "feedback-correct"
    elif ai_correct is False:
        status_icon, status_class = "❌", "feedback-incorrect"
    else:
        status_icon, status_class = "🤔", "feedback-partial"

    return HTMLResponse(
        f'<div class="exercise-card {status_class}" id="exercise-{exercise_id}">'
        f'<p class="exercise-question"><strong>{question}</strong></p>'
        f'<p><strong>你的答案：</strong>{answer}</p>'
        f'<p><strong>正确答案：</strong>{correct_answer}</p>'
        f'<div class="feedback">{status_icon} {feedback}</div>'
        f'</div>'
    )
