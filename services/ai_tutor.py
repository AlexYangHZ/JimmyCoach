"""AI Tutor service — DeepSeek API integration for teaching, grading, and chat."""

from pathlib import Path
from typing import AsyncGenerator, Any
import re

import yaml
from openai import AsyncOpenAI


class AITutorService:
    """Handles all DeepSeek API interactions."""

    def __init__(self, api_key: str, base_url: str, model: str, prompts_dir: Path):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.prompts_dir = Path(prompts_dir)
        self._prompts: dict[str, str] = {}

    def _load_prompt(self, name: str) -> str:
        """Load a system prompt from YAML, caching in memory."""
        if name not in self._prompts:
            path = self.prompts_dir / f"{name}.yaml"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                self._prompts[name] = data.get("system", "")
            else:
                self._prompts[name] = ""
        return self._prompts[name]

    def build_teach_messages(self, topic_meta: dict[str, Any]) -> list[dict[str, str]]:
        """Build message list for generating lesson content."""
        persona = self._load_prompt("tutor_base")
        teach = self._load_prompt("lesson_teach")

        system_content = f"{persona}\n\n{teach}"
        user_content = (
            f"请讲解以下知识点：\n"
            f"主题：{topic_meta.get('topic_id', '')}\n"
            f"难度：{topic_meta.get('difficulty_level', 1)}\n"
            f"教学方法建议：{topic_meta.get('teaching_approach', '')}"
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def build_grade_messages(
        self, exercise: dict[str, Any], student_answer: str, topic_context: str
    ) -> list[dict[str, str]]:
        """Build message list for grading an answer."""
        persona = self._load_prompt("tutor_base")
        grade = self._load_prompt("exercise_grade")

        system_content = f"{persona}\n\n{grade}"
        user_content = (
            f"当前学习主题：{topic_context}\n\n"
            f"题目：{exercise.get('question', '')}\n"
            f"题目类型：{exercise.get('type', '')}\n"
            f"正确答案：{exercise.get('correct', '')}\n"
            f"Jimmy的答案：{student_answer}\n\n"
            f"请评价Jimmy的答案。"
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def build_chat_messages(
        self,
        user_message: str,
        chat_history: list[dict[str, str]],
        topic_context: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        """Build message list for free-form chat."""
        persona = self._load_prompt("tutor_base")
        chat_prompt = self._load_prompt("chat_free")

        context_text = ""
        if topic_context:
            context_text = f"\n当前正在学习：{topic_context.get('title', topic_context.get('topic_id', ''))}"

        system_content = f"{persona}\n\n{chat_prompt}{context_text}"

        messages = [{"role": "system", "content": system_content}]
        messages.extend(chat_history[-10:])
        messages.append({"role": "user", "content": user_message})

        return messages

    async def grade_answer(
        self, exercise: dict[str, Any], student_answer: str, topic_context: str
    ) -> dict[str, Any]:
        """Grade an answer and return structured result. Non-streaming."""
        messages = self.build_grade_messages(exercise, student_answer, topic_context)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
            stream=False,
        )

        content = response.choices[0].message.content or ""

        is_correct = None
        match = re.search(r"对错:\s*(正确|错误|部分正确)", content)
        if match:
            status = match.group(1)
            if status == "正确":
                is_correct = True
            elif status == "错误":
                is_correct = False

        feedback = ""
        fb_match = re.search(r"反馈:\s*(.+)", content, re.DOTALL)
        if fb_match:
            feedback = fb_match.group(1).strip()

        return {"is_correct": is_correct, "feedback": feedback, "raw": content}

    async def stream_response(
        self, messages: list[dict[str, str]], temperature: float = 0.8, max_tokens: int = 800
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding content chunks."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
