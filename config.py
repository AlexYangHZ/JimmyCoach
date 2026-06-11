"""Application configuration loaded from environment variables and .env file."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Database
    database_url: str = "sqlite+aiosqlite:///jimmycoach.db"

    # App
    app_name: str = "JimmyCoach"
    data_dir: Path = Path("data")
    prompts_dir: Path = Path("prompts")


settings = Settings()

# Shared subject metadata
SUBJECT_NAMES = {"math": "数学", "english": "英语", "chinese": "语文", "science": "科学"}
SUBJECT_ICONS = {"math": "📐", "english": "🌐", "chinese": "📖", "science": "🔬"}
SUBJECT_DESCRIPTIONS = {
    "math": "涵盖数与代数、图形与几何等核心领域",
    "english": "人教版七年级英语，听说读写全面发展",
    "chinese": "统编版七年级语文，经典篇目与写作训练",
    "science": "科学探索，物理化学生物基础入门",
}
