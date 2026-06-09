#!/usr/bin/env python3
"""Split Math 7th Grade PDF into per-section files.

Usage: python3 scripts/split_pdf.py
Output: data/textbooks/math/grade7/pages/ (PDF files + PDF.js viewer)
"""

import fitz
from pathlib import Path

PDF_PATH = "docs/（人教版）义务教育教科书·数学七年级上册.pdf"
OUTPUT_DIR = Path("data/textbooks/math/grade7/pages")
PDF_OFFSET = 8  # textbook page 1 = PDF page 8

# Section definitions: (section_id, title, textbook_start_page, textbook_end_page)
# end_page is exclusive (start of next section or end of content)
SECTIONS = [
    # Chapter 1: 有理数 (textbook p1-23)
    ("ch01_sec01", "1.1 正数和负数", 2, 7),
    ("ch01_sec02", "1.2 有理数及其大小比较", 7, 21),
    ("ch01_reading", "阅读：用正负数表示允许偏差", 6, 7),
    ("ch01_history", "数学史：漫漫长路识负数", 18, 19),

    # Chapter 2: 有理数的运算 (textbook p24-63)
    ("ch02_sec01", "2.1 有理数的加法与减法", 25, 38),
    ("ch02_sec02", "2.2 有理数的乘法与除法", 38, 51),
    ("ch02_sec03", "2.3 有理数的乘方", 51, 59),

    # Chapter 3: 代数式 (textbook p68-87)
    ("ch03_sec01", "3.1 列代数式表示数量关系", 69, 79),
    ("ch03_sec02", "3.2 代数式的值", 79, 85),

    # Chapter 4: 整式的加减 (textbook p88-109)
    ("ch04_sec01", "4.1 整式", 89, 95),
    ("ch04_sec02", "4.2 整式的加法与减法", 95, 107),

    # Chapter 5: 一元一次方程 (textbook p110-148)
    ("ch05_sec01", "5.1 方程", 111, 120),
    ("ch05_sec02", "5.2 解一元一次方程", 120, 133),
    ("ch05_sec03", "5.3 实际问题与一元一次方程", 133, 145),

    # Chapter 6: 几何图形初步 (textbook p149-189)
    ("ch06_sec01", "6.1 几何图形", 150, 162),
    ("ch06_sec02", "6.2 直线、射线、线段", 162, 170),
    ("ch06_sec03", "6.3 角", 170, 184),
]


def tb_to_pdf(tb_page):
    """Convert textbook page to PDF page index (0-indexed)."""
    return tb_page + PDF_OFFSET


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(PDF_PATH)
    total_pages = doc.page_count
    print(f"PDF: {total_pages} pages total")

    for sec_id, title, start_tb, end_tb in SECTIONS:
        start_pdf = tb_to_pdf(start_tb)
        end_pdf = min(tb_to_pdf(end_tb), total_pages)

        if start_pdf >= total_pages:
            print(f"  SKIP {sec_id}: start page {start_pdf} beyond PDF ({total_pages})")
            continue

        # Create a new PDF with just these pages
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_pdf, to_page=end_pdf - 1)

        filename = f"{sec_id}.pdf"
        output_path = OUTPUT_DIR / filename
        new_doc.save(output_path)
        new_doc.close()

        page_count = end_pdf - start_pdf
        print(f"  {sec_id}: pages {start_pdf}-{end_pdf - 1} ({page_count} pg) → {filename}")
        print(f"    {title}")

    doc.close()

    # Count output
    pdfs = sorted(OUTPUT_DIR.glob("*.pdf"))
    total_size = sum(f.stat().st_size for f in pdfs)
    print(f"\n✅ Created {len(pdfs)} PDF files ({total_size:,} bytes)")
    print(f"   Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
