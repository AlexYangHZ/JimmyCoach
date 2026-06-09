"""Curriculum service — loads and queries YAML curriculum files."""

from pathlib import Path
from typing import Any
import yaml


class CurriculumService:
    """Loads curriculum data from YAML files on disk."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def _subject_dir(self, grade: int, subject: str) -> Path:
        return self.data_dir / f"grade{grade}" / subject

    def get_topics(self, grade: int, subject: str) -> list[dict[str, Any]]:
        """Return all topics for a grade/subject, sorted by order."""
        topics_path = self._subject_dir(grade, subject) / "topics.yaml"
        if not topics_path.exists():
            return []
        with open(topics_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        topics = data.get("topics", [])
        topics.sort(key=lambda t: t.get("order", 999))
        return topics

    def get_topic_meta(self, grade: int, subject: str, topic_id: str) -> dict[str, Any] | None:
        """Return learning goals and teaching notes for a topic."""
        meta_path = self._subject_dir(grade, subject) / topic_id / "meta.yaml"
        if not meta_path.exists():
            return None
        with open(meta_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_exercises(self, grade: int, subject: str, topic_id: str) -> list[dict[str, Any]]:
        """Return exercise templates for a topic."""
        ex_path = self._subject_dir(grade, subject) / topic_id / "exercises.yaml"
        if not ex_path.exists():
            return []
        with open(ex_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("exercises", [])

    @staticmethod
    def get_topic_by_id(topics: list[dict[str, Any]], topic_id: str) -> dict[str, Any] | None:
        """Find a topic dict in a topics list by id."""
        for t in topics:
            if t["id"] == topic_id:
                return t
        return None

    @staticmethod
    def get_next_topic(topics: list[dict[str, Any]], completed_ids: set[str]) -> dict[str, Any] | None:
        """Find the first topic not yet completed (respecting dependencies)."""
        for topic in topics:
            if topic["id"] in completed_ids:
                continue
            if all(dep in completed_ids for dep in topic.get("dependencies", [])):
                return topic
        return None

    def list_subjects(self, grade: int) -> list[str]:
        """List all subjects available for a grade."""
        grade_dir = self.data_dir / f"grade{grade}"
        if not grade_dir.exists():
            return []
        return [d.name for d in grade_dir.iterdir() if d.is_dir()]

    def get_subject_name(self, subject_id: str) -> str:
        """Map subject id to Chinese display name."""
        names = {"math": "数学", "chinese": "语文", "english": "英语", "science": "科学"}
        return names.get(subject_id, subject_id)
