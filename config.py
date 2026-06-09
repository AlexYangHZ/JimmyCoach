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
