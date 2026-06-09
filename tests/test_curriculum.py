"""Test curriculum loading from new textbook markdown structure."""

import pytest
import re
from pathlib import Path

from routes.pages import load_math_topics


def test_load_math_topics():
    topics = load_math_topics()

    assert len(topics) >= 14  # At least 14 knowledge points across 6 chapters
    # Check first topic
    assert topics[0]["title"] == "正数和负数"
    assert topics[0]["code"] == "1.1"
    assert "章" in topics[0]["chapter"]
    assert "有理数" in topics[0]["chapter"]


def test_topics_have_paths():
    topics = load_math_topics()
    for t in topics:
        assert t["path"].endswith(".md")
        assert t["id"] is not None


def test_all_chapters_covered():
    topics = load_math_topics()
    chapters = {t["chapter"] for t in topics}
    assert len(chapters) == 6  # 6 chapters


def test_topic_order():
    topics = load_math_topics()
    codes = [t["code"] for t in topics]
    # Verify sorted order
    assert codes[0] == "1.1"
    assert codes[-1] == "6.3"


def test_no_activity_in_topics():
    """Activities should not appear as topics."""
    topics = load_math_topics()
    for t in topics:
        assert "activity" not in t["path"]
        assert "README" not in t["path"]


def test_load_from_nonexistent_path():
    """Should return empty list for empty curriculum."""
    from routes.pages import SUBJECTS_CONFIG
    # English and Chinese don't have data yet
    assert len(SUBJECTS_CONFIG) == 3
    assert SUBJECTS_CONFIG[0]["id"] == "math"
