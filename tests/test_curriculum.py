"""Test curriculum YAML loading and querying."""

import pytest
from pathlib import Path

from services.curriculum import CurriculumService


@pytest.fixture
def curriculum_service():
    data_dir = Path(__file__).parent.parent / "data" / "curriculum"
    return CurriculumService(data_dir=data_dir)


def test_load_topics_for_subject(curriculum_service):
    topics = curriculum_service.get_topics(grade=6, subject="math")

    assert len(topics) == 3
    assert topics[0]["id"] == "fractions-basics"
    assert topics[1]["id"] == "fractions-multiply"
    assert topics[2]["id"] == "fractions-divide"
    assert topics[0]["order"] == 1
    assert topics[2]["order"] == 3


def test_get_topic_meta(curriculum_service):
    meta = curriculum_service.get_topic_meta(grade=6, subject="math", topic_id="fractions-basics")

    assert meta["topic_id"] == "fractions-basics"
    assert meta["difficulty_level"] == 1
    assert "混淆分子和分母" in meta["common_mistakes"]


def test_get_exercises(curriculum_service):
    exercises = curriculum_service.get_exercises(grade=6, subject="math", topic_id="fractions-basics")

    assert len(exercises) == 3
    assert exercises[0]["id"] == "ex-01"
    assert exercises[0]["type"] == "multiple_choice"


def test_topic_dependencies(curriculum_service):
    topics = curriculum_service.get_topics(grade=6, subject="math")

    bas = curriculum_service.get_topic_by_id(topics, "fractions-basics")
    mul = curriculum_service.get_topic_by_id(topics, "fractions-multiply")

    assert bas["dependencies"] == []
    assert "fractions-basics" in mul["dependencies"]


def test_topic_by_id_not_found(curriculum_service):
    topics = curriculum_service.get_topics(grade=6, subject="math")
    result = curriculum_service.get_topic_by_id(topics, "nonexistent")

    assert result is None


def test_get_next_topic(curriculum_service):
    topics = curriculum_service.get_topics(grade=6, subject="math")

    # Nothing completed → first topic
    next_topic = curriculum_service.get_next_topic(topics, set())
    assert next_topic["id"] == "fractions-basics"

    # First completed → second topic
    next_topic = curriculum_service.get_next_topic(topics, {"fractions-basics"})
    assert next_topic["id"] == "fractions-multiply"

    # All completed → None
    next_topic = curriculum_service.get_next_topic(topics, {"fractions-basics", "fractions-multiply", "fractions-divide"})
    assert next_topic is None


def test_empty_subject(curriculum_service):
    topics = curriculum_service.get_topics(grade=6, subject="chinese")
    assert topics == []
