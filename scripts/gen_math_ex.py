#!/usr/bin/env python3
"""Generate additional math exercises using DeepSeek API.

Usage:
    python3 scripts/gen_math_ex.py          # generate all 17 sections
    python3 scripts/gen_math_ex.py --dry-run  # preview prompts only

Output: data/exercises/math_candidates.json
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import yaml
from openai import AsyncOpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings


def load_sections() -> list[dict]:
    """Load math section IDs and titles from existing exercises."""
    path = Path("data/exercises/exercises.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Map section IDs to titles using the hardcoded data from pages.py
    titles = {
        "ch01_sec01": "正数和负数",
        "ch01_sec02": "有理数及其大小比较",
        "ch01_reading": "用正负数表示允许偏差",
        "ch01_history": "漫漫长路识负数",
        "ch02_sec01": "有理数的加法与减法",
        "ch02_sec02": "有理数的乘法与除法",
        "ch02_sec03": "有理数的乘方",
        "ch03_sec01": "列代数式表示数量关系",
        "ch03_sec02": "代数式的值",
        "ch04_sec01": "整式",
        "ch04_sec02": "整式的加法与减法",
        "ch05_sec01": "从算式到方程",
        "ch05_sec02": "解一元一次方程",
        "ch05_sec03": "实际问题与一元一次方程",
        "ch06_sec01": "几何图形",
        "ch06_sec02": "直线、射线、线段",
        "ch06_sec03": "角",
    }

    sections = []
    for sid in data:
        if sid == "default":
            continue
        sections.append({
            "id": sid,
            "title": titles.get(sid, sid),
        })
    return sections


def load_keypoints(section_id: str) -> dict:
    """Load key concepts for a math section."""
    path = Path("data/keypoints/math_grade7.py")
    if not path.exists():
        return {}
    # Dynamic import
    import importlib.util
    spec = importlib.util.spec_from_file_location("math_kp", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    kp = mod.get_keypoints(section_id) if hasattr(mod, 'get_keypoints') else None
    return kp or {}


def load_textbook_text(section_id: str) -> str:
    """Load textbook markdown for a section."""
    # Math sections: ch01_sec01 maps to chapter_01/section_01.md
    match = re.match(r"ch(\d+)_(\w+)", section_id)
    if not match:
        return ""
    ch_num = int(match.group(1))
    sec_part = match.group(2)

    # Determine filename
    md_dir = Path(f"data/textbooks/math/grade7/chapter_{ch_num:02d}")
    if sec_part.startswith("sec"):
        sec_num = int(sec_part.replace("sec", ""))
        md_path = md_dir / f"section_{sec_num:02d}.md"
    elif sec_part == "reading":
        md_path = md_dir / "activity_用正负数表示允许偏差.md"
    elif sec_part == "history":
        md_path = md_dir / "activity_漫漫长路识负数.md"
    else:
        return ""

    if md_path.exists():
        return md_path.read_text(encoding="utf-8")[:2000]
    return ""


def load_system_prompt() -> str:
    path = Path("prompts/exercise_gen_math.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("system", "")


def build_user_prompt(section: dict, keypoints: dict, textbook_text: str) -> str:
    concepts = keypoints.get("concepts", [])
    formulas = keypoints.get("formulas", [])
    concepts_str = "\n".join(f"  - {c}" for c in concepts) if concepts else "  (无)"
    formulas_str = "\n".join(f"  - {f}" for f in formulas) if formulas else "  (无)"

    return f"""为以下数学知识点生成5道新的练习题。

章节：{section['title']}

核心概念：
{concepts_str}

重要公式/法则：
{formulas_str}

教材内容参考：
{textbook_text[:1500]}

请生成5道与现有题目不重复的新练习题。侧重概念理解和基础计算。"""


async def generate_exercises(client, model, system_prompt, user_prompt, retries=3):
    for attempt in range(retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=False,
            )
            raw = response.choices[0].message.content or "{}"
            m = re.search(r"\{[\s\S]*\}", raw)
            parsed = json.loads(m.group() if m else raw)
            exercises = parsed.get("exercises", [])

            for ex in exercises:
                if ex["type"] == "choice":
                    assert isinstance(ex.get("answer"), int)
                    assert isinstance(ex.get("choices"), list)
                elif ex["type"] == "fill":
                    assert isinstance(ex.get("answer"), str)
                elif ex["type"] == "true_false":
                    assert ex.get("answer") in ("正确", "错误")

            return {"exercises": exercises}
        except (json.JSONDecodeError, KeyError, AssertionError) as e:
            print(f"  Parse error (attempt {attempt+1}): {e}")
            if attempt == retries - 1:
                return {"exercises": [], "error": str(e)}
            await asyncio.sleep(1)
        except Exception as e:
            print(f"  API error (attempt {attempt+1}): {e}")
            if attempt == retries - 1:
                return {"exercises": [], "error": str(e)}
            await asyncio.sleep(2)
    return {"exercises": []}


async def main(dry_run=False):
    sections = load_sections()
    system_prompt = load_system_prompt()
    print(f"Math sections: {len(sections)}")
    print(f"System prompt: {len(system_prompt)} chars\n")

    if dry_run:
        for sec in sections[:3]:
            kp = load_keypoints(sec["id"])
            text = load_textbook_text(sec["id"])
            prompt = build_user_prompt(sec, kp, text)
            print(f"=== {sec['id']}: {sec['title']} ===")
            print(f"Keypoints: concepts={len(kp.get('concepts',[]))}, formulas={len(kp.get('formulas',[]))}")
            print(f"Textbook text: {len(text)} chars")
            print(f"Prompt: {len(prompt)} chars\n")
        return

    client = AsyncOpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    results = {}

    for i, sec in enumerate(sections):
        label = f"[{i+1}/{len(sections)}] {sec['id']}: {sec['title']}"
        print(f"{label} ... ", end="", flush=True)

        kp = load_keypoints(sec["id"])
        text = load_textbook_text(sec["id"])
        prompt = build_user_prompt(sec, kp, text)
        result = await generate_exercises(client, settings.deepseek_model, system_prompt, prompt)

        exercises = result.get("exercises", [])
        if result.get("error"):
            print(f"FAILED: {result['error']}")
        else:
            print(f"OK ({len(exercises)} exercises)")

        results[sec["id"]] = result

    output_path = Path("data/exercises/math_candidates.json")
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {output_path}")

    total = sum(len(r.get("exercises", [])) for r in results.values())
    errors = sum(1 for r in results.values() if r.get("error"))
    print(f"Total: {total} exercises, Errors: {errors} sections")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry_run))
