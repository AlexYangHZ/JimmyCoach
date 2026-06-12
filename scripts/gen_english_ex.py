#!/usr/bin/env python3
"""Generate additional English exercises using DeepSeek API with improved prompt.

Usage:
    python3 scripts/gen_english_ex.py          # generate all 10 sections
    python3 scripts/gen_english_ex.py --dry-run  # preview prompts only

Output: data/exercises/english_candidates.json
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import yaml
from openai import AsyncOpenAI

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings


# ---- Load content helpers ----

def load_sections() -> list[dict]:
    path = Path("data/textbooks/english/grade7/sections.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_keypoints() -> dict:
    path = Path("data/keypoints/english_grade7.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_textbook_text(section: dict) -> str:
    """Load textbook markdown text for a section's chapter."""
    sec_id = section["id"]  # e.g. ch02_sec01
    chapter_num = sec_id.split("_")[0].replace("ch", "")  # e.g. "02"
    md_path = Path(f"data/textbooks/english/grade7/chapter_{chapter_num}/section_se.md")
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
        # Extract the relevant part for this section based on section label
        # Section A or B marker
        section_label = "A" if "sec01" in sec_id else "B"
        return text[:2000]  # truncate to keep prompt manageable
    return ""


def load_system_prompt() -> str:
    path = Path("prompts/exercise_gen_english.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("system", "")


def build_user_prompt(section: dict, keypoints: dict, textbook_text: str) -> str:
    """Build a section-specific user prompt."""
    sec_id = section["id"]
    kp = keypoints.get(sec_id, {})

    concepts = kp.get("concepts", [])
    formulas = kp.get("formulas", [])
    tips = kp.get("tips", [])

    concepts_str = "\n".join(f"  - {c}" for c in concepts) if concepts else "  (none provided)"
    formulas_str = "\n".join(f"  - {f}" for f in formulas) if formulas else "  (none provided)"

    return f"""Generate 5 new English practice exercises for this textbook section.

Section Title: {section['title']}
Chapter: {section['chapter']}

Key Concepts:
{concepts_str}

Key Sentence Patterns:
{formulas_str}

Textbook Content Excerpt:
{textbook_text[:1500]}

Please generate 5 exercises that are DIFFERENT from standard greeting/self-introduction drills. Focus on the specific vocabulary, grammar, and content from this section."""


# ---- API call ----

async def generate_exercises(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    retries: int = 3,
) -> dict:
    """Call DeepSeek API to generate exercises."""
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

            # Validate structure
            for ex in exercises:
                if ex["type"] == "choice":
                    assert isinstance(ex.get("answer"), int), "choice answer must be int"
                    assert isinstance(ex.get("choices"), list), "choices must be list"
                elif ex["type"] == "fill":
                    assert isinstance(ex.get("answer"), str), "fill answer must be string"
                elif ex["type"] == "true_false":
                    assert ex.get("answer") in ("正确", "错误"), "true_false answer must be 正确/错误"

            return {"exercises": exercises}

        except (json.JSONDecodeError, KeyError, AssertionError) as e:
            print(f"  Parse/validation error (attempt {attempt+1}): {e}")
            if attempt == retries - 1:
                return {"exercises": [], "error": str(e)}
            await asyncio.sleep(1)
        except Exception as e:
            print(f"  API error (attempt {attempt+1}): {e}")
            if attempt == retries - 1:
                return {"exercises": [], "error": str(e)}
            await asyncio.sleep(2)

    return {"exercises": []}


# ---- Main ----

async def main(dry_run: bool = False):
    sections = load_sections()
    keypoints = load_keypoints()
    system_prompt = load_system_prompt()

    print(f"System prompt loaded ({len(system_prompt)} chars)")
    print(f"Sections: {len(sections)}")
    print()

    if dry_run:
        for sec in sections:
            text = load_textbook_text(sec)
            user_prompt = build_user_prompt(sec, keypoints, text)
            print(f"=== {sec['id']}: {sec['title']} ===")
            print(f"User prompt length: {len(user_prompt)} chars")
            print(f"Textbook text length: {len(text)} chars")
            print()
        return

    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    results = {}
    for i, sec in enumerate(sections):
        sec_id = sec["id"]
        label = f"[{i+1}/{len(sections)}] {sec_id}: {sec['title'][:50]}"
        print(f"{label} ... ", end="", flush=True)

        text = load_textbook_text(sec)
        user_prompt = build_user_prompt(sec, keypoints, text)
        result = await generate_exercises(client, settings.deepseek_model, system_prompt, user_prompt)

        exercises = result.get("exercises", [])
        if result.get("error"):
            print(f"FAILED: {result['error']}")
        else:
            print(f"OK ({len(exercises)} exercises)")

        results[sec_id] = result

    # Save
    output_path = Path("data/exercises/english_candidates.json")
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {output_path}")

    # Summary
    total = sum(len(r.get("exercises", [])) for r in results.values())
    errors = sum(1 for r in results.values() if r.get("error"))
    print(f"Total generated: {total} exercises across {len(results)} sections")
    if errors:
        print(f"Sections with errors: {errors}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry_run))
