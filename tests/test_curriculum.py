"""Test curriculum loading for math 七年级上册."""

import pytest
import re
from pathlib import Path

from routes.pages import MATH_SECTIONS


def test_math_sections_count():
    """17 sections covering 6 chapters."""
    assert len(MATH_SECTIONS) == 17


def test_first_section():
    assert MATH_SECTIONS[0]["title"] == "正数和负数"
    assert MATH_SECTIONS[0]["code"] == "1.1"
    assert "有理数" in MATH_SECTIONS[0]["chapter"]


def test_all_sections_have_pdf():
    for s in MATH_SECTIONS:
        assert s["pdf"].endswith(".pdf")
        assert s["id"] is not None
        assert s["pages"] > 0


def test_six_chapters_covered():
    chapters = {s["chapter"] for s in MATH_SECTIONS}
    assert len(chapters) == 6


def test_section_codes_ordered():
    """Check code ordering matches list order."""
    codes = [s["code"] for s in MATH_SECTIONS[:5]]
    assert codes[0] == "1.1"
    assert codes[1] == "1.2"


def test_subjects_config():
    from routes.pages import SUBJECT_CATALOG
    assert len(SUBJECT_CATALOG) == 3
    assert SUBJECT_CATALOG[0]["id"] == "math"
    assert SUBJECT_CATALOG[0]["grades"][0]["ready"] is True
