"""Add textbook metadata chunks for structural queries (chapter count, etc.)."""
from pathlib import Path
import json

for subject in ["english", "math"]:
    sections_file = Path(f"data/textbooks/{subject}/grade7/sections.json")
    if not sections_file.exists():
        continue

    with open(sections_file) as f:
        sections = json.load(f)

    chapters = {}
    for s in sections:
        ch = s.get("chapter", "")
        if ch not in chapters:
            chapters[ch] = []
        chapters[ch].append(s["title"])

    meta_lines = [f"这本教材共有 {len(chapters)} 章："]
    for i, (ch, titles) in enumerate(chapters.items(), 1):
        meta_lines.append(f"第{i}章：{ch}，包含 {len(titles)} 个知识点：{'、'.join(titles)}")

    meta_text = "\n".join(meta_lines)
    meta_dir = Path(f"data/textbooks/{subject}/grade7")
    meta_file = meta_dir / "INDEX.md"
    meta_file.write_text(f"# {subject} 教材结构说明\n\n{meta_text}", encoding="utf-8")

    # Rebuild retriever
    from services.retriever import MathRetriever
    cache = Path(f"data/vectordb/{subject}/retriever.pkl")
    if cache.exists():
        cache.unlink()
    r = MathRetriever(markdown_dir=meta_dir, cache_path=cache)
    r.build_index()
    print(f"{subject}: rebuilt, {len(r.documents)} docs")
