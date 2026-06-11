"""Pipeline service — automated PDF-to-knowledge-point processing."""

import json, re, shutil, time, asyncio
from pathlib import Path
from datetime import datetime, timezone

import fitz
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai_tutor import get_ai_tutor
from config import settings, SUBJECT_ICONS

TOC_PARSE_PROMPT = """你是教材分析专家。以下是教材目录页文本。请提取每章每节信息，返回JSON。

目录文本：
{text}

严格按以下JSON格式返回（只返回JSON）：
{{
  "chapters": [
    {{
      "num": 1,
      "title": "章标题",
      "start_page": 1,
      "sections": [
        {{"num": 1, "title": "1.1 节标题", "start_page": 2}}
      ]
    }}
  ]
}}
注意：只提取正文知识点章节，跳过数学活动、小结、阅读材料等。start_page是课本页码。"""

KEYPOINTS_PROMPT = """你是数学教育专家。请为以下知识点提炼关键内容，返回JSON。

知识点：{title}
教材内容：
{content}

严格返回JSON：
{{
  "concepts": ["核心概念1", "概念2", "概念3"],
  "formulas": ["公式定理1", "公式2"],
  "tips": ["学习提示1", "提示2"]
}}
concepts: 3-5个, formulas: 1-3个(无则空数组), tips: 1-3个"""

MINDMAP_PROMPT = """创建知识点思维导图，返回JSON。

知识点：{title}  所属章节：{chapter}
教材内容：{content}

JSON格式：
{{
  "label": "知识点名",
  "children": [
    {{"label": "分支1", "children": [{{"label": "子点1"}}, {{"label": "子点2"}}]}},
    {{"label": "分支2", "children": [{{"label": "子点3"}}]}}
  ]
}}
3-5个分支，每分支2-4子点，不超过3层。"""

EXERCISES_PROMPT = """为知识点生成5道练习题，返回JSON。

知识点：{title}
教材内容：{content}

JSON格式：
{{
  "exercises": [
    {{"type": "choice", "question": "题", "choices": ["A","B","C","D"], "answer": 0, "explanation": "解析"}},
    {{"type": "fill", "question": "题", "answer": "答案", "explanation": "解析"}},
    {{"type": "choice", "question": "题", "choices": ["A","B","C","D"], "answer": 2, "explanation": "解析"}},
    {{"type": "fill", "question": "题", "answer": "答案", "explanation": "解析"}},
    {{"type": "true_false", "question": "题", "answer": "正确", "explanation": "解析"}}
  ]
}}
2选择+2填空+1判断。answer: 选择题用索引0-3, 填空用字符串, 判断用"正确"/"错误"。"""


class PipelineService:
    """Orchestrates PDF→knowledge-point pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai = get_ai_tutor()

    async def update_task(self, task_id: int, **kwargs):
        from db.models import PipelineTask
        task = await self.db.get(PipelineTask, task_id)
        if task:
            for k, v in kwargs.items():
                setattr(task, k, v)
            task.updated_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def _ai_json(self, prompt: str, retries: int = 3) -> dict:
        for attempt in range(retries):
            try:
                response = await self.ai.client.chat.completions.create(
                    model=self.ai.model, messages=[{"role": "user", "content": prompt}],
                    temperature=0.7, max_tokens=2000, stream=False,
                )
                raw = response.choices[0].message.content or "{}"
                m = re.search(r'\{[\s\S]*\}', raw)
                return json.loads(m.group() if m else raw)
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                print(f"[Pipeline] AI JSON parse error (attempt {attempt+1}): {e}")
                if attempt == retries - 1:
                    return {}
                await asyncio.sleep(1)
            except Exception as e:
                print(f"[Pipeline] AI API error (attempt {attempt+1}): {e}")
                if attempt == retries - 1:
                    return {}
                await asyncio.sleep(1)

    async def phase1_extract(self, task_id: int) -> dict:
        from db.models import PipelineTask
        task = await self.db.get(PipelineTask, task_id)
        await self.update_task(task_id, status="phase1", progress=10)

        doc = fitz.open(task.pdf_path)
        toc_text = ""
        for i in range(min(3, doc.page_count), min(12, doc.page_count)):
            toc_text += doc[i].get_text() + "\n"
        doc.close()

        await self.update_task(task_id, progress=30)
        chapters_data = await self._ai_json(TOC_PARSE_PROMPT.format(text=toc_text[:3000]))
        await self.update_task(task_id, status="awaiting_confirm", progress=100,
                               chapters_json=json.dumps(chapters_data, ensure_ascii=False))
        return chapters_data

    async def phase2_process(self, task_id: int, confirmed_chapters: dict):
        from db.models import PipelineTask
        task = await self.db.get(PipelineTask, task_id)
        subject, grade = task.subject, task.grade
        await self.update_task(task_id, status="phase2", progress=0)

        base = Path(f"data/textbooks/{subject}/grade{grade}")
        pages_dir = base / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(task.pdf_path, pages_dir / "full.pdf")

        doc = fitz.open(task.pdf_path)
        total_pages = doc.page_count
        PDF_OFFSET = 8

        chapters = confirmed_chapters.get("chapters", [])
        all_sections = []
        for ch in chapters:
            for s in ch.get("sections", []):
                all_sections.append({**s, "chapter": f"第{ch['num']}章 {ch['title']}"})

        total = len(all_sections) * 4
        done = 0

        sections_config = []
        all_exercises = {}
        all_keypoints = {}
        all_mindmaps = {}

        for i, s in enumerate(all_sections):
            ch_num = next((ch["num"] for ch in chapters
                          if any(ss["title"] == s["title"] for ss in ch.get("sections", []))), i + 1)
            sec_id = f"ch{ch_num:02d}_sec{s['num']:02d}"

            # PDF split
            start_pdf = max(0, s["start_page"] + PDF_OFFSET)
            end_pdf = min(start_pdf + 10, total_pages)
            if i + 1 < len(all_sections):
                end_pdf = min(all_sections[i + 1]["start_page"] + PDF_OFFSET, total_pages)

            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start_pdf, to_page=end_pdf - 1)
            new_doc.save(pages_dir / f"{sec_id}.pdf")
            new_doc.close()

            sections_config.append({
                "id": sec_id, "code": f"{ch_num}.{s['num']}",
                "title": s["title"], "chapter": s["chapter"],
                "pdf": f"{sec_id}.pdf", "pages": max(1, end_pdf - start_pdf),
            })
            done += 1
            await self.update_task(task_id, progress=int(done / total * 100))

            # Extract content for AI
            content_text = ""
            for p in range(start_pdf, min(end_pdf, total_pages)):
                content_text += doc[p].get_text()
            content_text = content_text[:2500]

            # AI generation
            all_keypoints[sec_id] = await self._ai_json(
                KEYPOINTS_PROMPT.format(title=s["title"], content=content_text))
            done += 1
            await self.update_task(task_id, progress=int(done / total * 100))

            all_mindmaps[sec_id] = await self._ai_json(
                MINDMAP_PROMPT.format(title=s["title"], chapter=s["chapter"], content=content_text[:1200]))
            done += 1
            await self.update_task(task_id, progress=int(done / total * 100))

            ex_result = await self._ai_json(
                EXERCISES_PROMPT.format(title=s["title"], content=content_text))
            all_exercises[sec_id] = ex_result.get("exercises", [])
            done += 1
            await self.update_task(task_id, progress=int(done / total * 100))

        doc.close()

        # Save data files
        self._save_json(Path(f"data/keypoints/{subject}_grade{grade}.json"), all_keypoints)
        self._save_json(Path(f"data/mindmaps/{subject}_grade{grade}.json"), all_mindmaps)
        all_exercises["default"] = [{"type": "choice", "question": "请先学习教材内容",
                                      "choices": ["知道了"], "answer": 0, "explanation": ""}]
        self._save_json(Path(f"data/exercises/{subject}.json"), all_exercises)
        self._save_json(base / "sections.json", sections_config)

        await self.update_task(task_id, status="phase3", progress=90)

        # Generate markdown files from extracted PDF text for retriever
        md_dir = base
        md_dir.mkdir(parents=True, exist_ok=True)
        for s, sec in zip(all_sections, sections_config):
            ch_num = sec['id'][2:4]
            sec_num = sec['id'][-2:]
            ch_dir = md_dir / f"chapter_{ch_num}"
            ch_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = pages_dir / sec["pdf"]
            content = f"# {sec['title']}\n\n所属章节: {sec['chapter']}"
            if pdf_path.exists():
                try:
                    extract_doc = fitz.open(pdf_path)
                    text_parts = []
                    for page in extract_doc:
                        text_parts.append(page.get_text())
                    extract_doc.close()
                    content = f"# {sec['title']}\n\n" + "\n\n".join(text_parts)
                except Exception:
                    pass
            (ch_dir / f"section_{sec_num}.md").write_text(content, encoding="utf-8")

        from services.retriever import MathRetriever
        cache = Path(f"data/vectordb/{subject}/retriever.pkl")
        cache.parent.mkdir(parents=True, exist_ok=True)
        r = MathRetriever(markdown_dir=md_dir, cache_path=cache)
        r.build_index()

        await self._register_in_catalog(subject, task.subject_name, grade, task.semester, len(sections_config))
        await self.update_task(task_id, status="done", progress=100)

    def _save_json(self, path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def _register_in_catalog(self, subject, subject_name, grade, semester, topic_count):
        """Update SUBJECT_CATALOG to mark this subject as ready (thread-safe)."""
        from routes.pages import SUBJECT_CATALOG, _catalog_lock
        async with _catalog_lock:
            for subj in SUBJECT_CATALOG:
                if subj["id"] == subject:
                    for g in subj["grades"]:
                        if g["grade"] == grade and g["semester"] == semester:
                            g["ready"] = True
                            g["topic_count"] = topic_count
                            return
                    subj["grades"].append({
                        "grade": grade, "semester": semester, "ready": True,
                        "pdf_url": f"/textbook/{subject}/grade{grade}/pages/full.pdf",
                        "topic_count": topic_count,
                    })
                    return
            SUBJECT_CATALOG.append({
                "id": subject, "name": subject_name,
                "icon": SUBJECT_ICONS.get(subject, "📚"),
                "description": f"{subject_name} {grade}年级{semester}",
                "grades": [{"grade": grade, "semester": semester, "ready": True,
                            "pdf_url": f"/textbook/{subject}/grade{grade}/pages/full.pdf",
                            "topic_count": topic_count}],
            })


def get_pipeline(db: AsyncSession) -> PipelineService:
    return PipelineService(db)
