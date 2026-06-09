"""Chat context service — builds conversation context for AI prompts."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LessonContext:
    """Context about what Jimmy is currently studying."""
    topic_id: str = ""
    topic_title: str = ""
    grade: int = 6
    subject: str = ""
    key_points: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)


class ChatContextService:
    """Manages conversation context for AI interactions."""

    @staticmethod
    def make_lesson_context(
        topic: dict[str, Any] | None,
        topic_meta: dict[str, Any] | None,
        grade: int = 6,
        subject: str = "",
    ) -> LessonContext:
        """Create a LessonContext from topic and meta data."""
        if topic is None:
            return LessonContext()

        return LessonContext(
            topic_id=topic.get("id", ""),
            topic_title=topic.get("title", ""),
            grade=grade,
            subject=subject,
            key_points=topic.get("key_points", []),
            common_mistakes=topic_meta.get("common_mistakes", []) if topic_meta else [],
        )

    @staticmethod
    def build_topic_context_text(ctx: LessonContext) -> str:
        """Render lesson context as a string for the AI prompt."""
        if not ctx.topic_id:
            return ""
        parts = [
            f"当前学习主题：{ctx.topic_title}",
            f"年级：{ctx.grade}年级",
        ]
        if ctx.key_points:
            parts.append(f"学习重点：{'、'.join(ctx.key_points)}")
        if ctx.common_mistakes:
            parts.append(f"常见错误：{'、'.join(ctx.common_mistakes)}")
        return "\n".join(parts)

    @staticmethod
    def context_for_chat(ctx: LessonContext) -> dict[str, Any] | None:
        """Build the context dict for AI chat messages, or None if empty."""
        if not ctx.topic_id:
            return None
        return {
            "topic_id": ctx.topic_id,
            "title": ctx.topic_title,
            "key_points": ctx.key_points,
        }
