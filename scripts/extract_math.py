#!/usr/bin/env python3
"""Extract Math 7th Grade (上册) PDF -> structured Markdown by chapter/section.

Usage: python3 scripts/extract_math.py
Output: data/textbooks/math/grade7/chapter_*/section_*.md
"""

import fitz
import re
from pathlib import Path

PDF_PATH = "docs/（人教版）义务教育教科书·数学七年级上册.pdf"
OUTPUT_DIR = Path("data/textbooks/math/grade7")

# PDF page offset: textbook page 1 corresponds to PDF page 8
# (Cover=0-2, Copyright=3, StudentLetter=4, TOC=5-7, Chapter1 starts=8)
PDF_OFFSET = 8

# Chapter/Section structure from TOC (textbook page numbers)
CHAPTERS = [
    {
        "num": 1, "title": "有理数",
        "intro_tb_page": 1,  # textbook page where chapter intro starts
        "sections": [
            {"num": 1, "title": "正数和负数", "tb_page": 2},
            {"num": 2, "title": "有理数及其大小比较", "tb_page": 7},
        ],
        "activities": [
            {"type": "reading", "title": "用正负数表示允许偏差", "tb_page": 6},
            {"type": "math_history", "title": "漫漫长路识负数", "tb_page": 18},
        ],
        "summary_tb_page": 21,
    },
    {
        "num": 2, "title": "有理数的运算",
        "intro_tb_page": 24,
        "sections": [
            {"num": 1, "title": "有理数的加法与减法", "tb_page": 25},
            {"num": 2, "title": "有理数的乘法与除法", "tb_page": 38},
            {"num": 3, "title": "有理数的乘方", "tb_page": 51},
        ],
        "activities": [
            {"type": "reading", "title": "我国古代的正负数加减运算法则——正负术", "tb_page": 37},
            {"type": "discovery", "title": "从数系扩充看有理数乘法法则", "tb_page": 50},
        ],
        "summary_tb_page": 59,
    },
    {
        "num": 3, "title": "代数式",
        "intro_tb_page": 68,
        "sections": [
            {"num": 1, "title": "列代数式表示数量关系", "tb_page": 69},
            {"num": 2, "title": "代数式的值", "tb_page": 79},
        ],
        "activities": [
            {"type": "reading", "title": "数字1与字母X的对话", "tb_page": 78},
        ],
        "summary_tb_page": 85,
    },
    {
        "num": 4, "title": "整式的加减",
        "intro_tb_page": 88,
        "sections": [
            {"num": 1, "title": "整式", "tb_page": 89},
            {"num": 2, "title": "整式的加法与减法", "tb_page": 95},
        ],
        "summary_tb_page": 107,
    },
    {
        "num": 5, "title": "一元一次方程",
        "intro_tb_page": 110,
        "sections": [
            {"num": 1, "title": "方程", "tb_page": 111},
            {"num": 2, "title": "解一元一次方程", "tb_page": 120},
            {"num": 3, "title": "实际问题与一元一次方程", "tb_page": 133},
        ],
        "activities": [
            {"type": "discovery", "title": "无限循环小数化分数", "tb_page": 132},
            {"type": "reading", "title": "初步认识数学模型", "tb_page": 142},
        ],
        "summary_tb_page": 145,
    },
    {
        "num": 6, "title": "几何图形初步",
        "intro_tb_page": 149,
        "sections": [
            {"num": 1, "title": "几何图形", "tb_page": 150},
            {"num": 2, "title": "直线、射线、线段", "tb_page": 162},
            {"num": 3, "title": "角", "tb_page": 170},
        ],
        "activities": [
            {"type": "math_history", "title": "几何的起源", "tb_page": 160},
            {"type": "reading", "title": "长度的测量", "tb_page": 168},
            {"type": "reading", "title": "角的度量", "tb_page": 180},
        ],
        "summary_tb_page": 184,
    },
]


def tb_to_pdf(tb_page):
    """Convert textbook page number to PDF page index."""
    return tb_page + PDF_OFFSET


def sanitize_text(text):
    """Clean up extracted text."""
    # Remove excessive blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Remove isolated page numbers
    text = re.sub(r"\n\s*\d{1,3}\s*\n(?=\n|$)", "\n", text)
    # Remove standalone numbers at end of page
    text = re.sub(r"\n\d{1,3}\s*$", "", text)
    # Fix special chars
    text = text.replace("", "").replace("", "•")
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_page_range(doc, start_tb, end_tb):
    """Extract text from textbook page range [start_tb, end_tb)."""
    start_pdf = tb_to_pdf(start_tb)
    end_pdf = tb_to_pdf(end_tb)
    end_pdf = min(end_pdf, doc.page_count)

    # Safety: clamp to valid range
    start_pdf = max(0, min(start_pdf, doc.page_count - 1))

    texts = []
    for pdf_idx in range(start_pdf, end_pdf):
        page = doc[pdf_idx]
        texts.append(page.get_text())

    return sanitize_text("\n".join(texts))


def extract_single_page(doc, tb_page):
    """Extract text from a single textbook page."""
    return extract_page_range(doc, tb_page, tb_page + 1)


def create_markdown_files(doc):
    """Create structured markdown files for each chapter and section."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_pages_covered = set()

    for ch in CHAPTERS:
        ch_dir = OUTPUT_DIR / f"chapter_{ch['num']:02d}"
        ch_dir.mkdir(parents=True, exist_ok=True)

        # Chapter introduction text (from chapter start to first section)
        first_section_tb = ch["sections"][0]["tb_page"]
        intro_text = extract_page_range(doc, ch["intro_tb_page"], first_section_tb)
        ch_md = f"# 第{ch['num']}章 {ch['title']}\n\n## 章节导入\n\n{intro_text}\n"
        (ch_dir / "README.md").write_text(ch_md, encoding="utf-8")

        # Sections (knowledge points)
        for i, sec in enumerate(ch["sections"]):
            sec_start = sec["tb_page"]
            # End at next section, or chapter summary
            if i + 1 < len(ch["sections"]):
                sec_end = ch["sections"][i + 1]["tb_page"]
            else:
                sec_end = ch.get("summary_tb_page", sec_start + 30)

            # Extended range to catch content that spans across pages
            sec_text = extract_page_range(doc, sec_start, sec_end)

            sec_filename = f"section_{sec['num']:02d}.md"
            sec_md = f"# {ch['num']}.{sec['num']} {sec['title']}\n\n"
            sec_md += f"**所属章节**: 第{ch['num']}章 {ch['title']}\n\n"
            sec_md += f"---\n\n{sec_text}\n"

            (ch_dir / sec_filename).write_text(sec_md, encoding="utf-8")

            # Track pages
            for p in range(sec_start, sec_end):
                total_pages_covered.add(p)

        # Activities & special sections
        for act in ch.get("activities", []):
            # Extract 1-2 pages around the activity
            act_text = extract_page_range(doc, act["tb_page"], act["tb_page"] + 2)
            safe_name = re.sub(r"[—\-]", "-", act["title"])
            safe_name = re.sub(r"[^\w一-鿿\-]", "_", safe_name)[:50]
            act_filename = f"activity_{safe_name}.md"
            act_md = f"# {act['title']}\n\n"
            act_md += f"**类型**: {act['type']}\n"
            act_md += f"**所属章节**: 第{ch['num']}章 {ch['title']}\n\n"
            act_md += f"---\n\n{act_text}\n"
            (ch_dir / act_filename).write_text(act_md, encoding="utf-8")

    # Generate index
    lines = ["# 人教版数学七年级上册 — 知识点索引\n"]
    lines.append(f"\n> 共 {len(CHAPTERS)} 章，自动提取自PDF教材\n")

    for ch in CHAPTERS:
        lines.append(f"\n## 第{ch['num']}章 {ch['title']}")
        lines.append(f"\n- [章节概述](chapter_{ch['num']:02d}/README.md)")

        for sec in ch["sections"]:
            lines.append(
                f"  - [{ch['num']}.{sec['num']} {sec['title']}]"
                f"(chapter_{ch['num']:02d}/section_{sec['num']:02d}.md)"
            )

        for act in ch.get("activities", []):
            safe_name = re.sub(r"[—\-]", "-", act["title"])
            safe_name = re.sub(r"[^\w一-鿿\-]", "_", safe_name)[:50]
            lines.append(
                f"  - [{act['title']}]"
                f"(chapter_{ch['num']:02d}/activity_{safe_name}.md)"
            )

    (OUTPUT_DIR / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Covered {len(total_pages_covered)} unique textbook pages")
    return OUTPUT_DIR


def main():
    print(f"Opening: {PDF_PATH}")
    doc = fitz.open(PDF_PATH)
    print(f"Total PDF pages: {doc.page_count}")
    print(f"Content pages: {doc.page_count - PDF_OFFSET} (textbook pages 1-{doc.page_count - PDF_OFFSET})")

    output_dir = create_markdown_files(doc)

    md_files = sorted(output_dir.rglob("*.md"))
    total_bytes = sum(f.stat().st_size for f in md_files)
    print(f"\nCreated {len(md_files)} files ({total_bytes:,} bytes):")

    for f in md_files:
        size = f.stat().st_size
        marker = "✅" if size > 1000 else "⚠️"
        print(f"  {marker} {f.relative_to(output_dir)} ({size:,} bytes)")

    doc.close()


if __name__ == "__main__":
    main()
