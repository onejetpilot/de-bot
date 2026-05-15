from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    interview_question_count: int = Field(default=50, alias="INTERVIEW_QUESTION_COUNT")
    database_file: Path = Field(
        default=BASE_DIR / "data" / "bot.sqlite3",
        alias="DATABASE_FILE",
    )
    questions_file: Path = Field(
        default=BASE_DIR / "data" / "questions.md",
        alias="QUESTIONS_FILE",
    )
    generated_questions_file: Path = Field(
        default=BASE_DIR / "data" / "generated_questions.json",
        alias="GENERATED_QUESTIONS_FILE",
    )
    interview_results_file: Path = Field(
        default=BASE_DIR / "data" / "interview_results.json",
        alias="INTERVIEW_RESULTS_FILE",
    )
    answer_cache_file: Path = Field(
        default=BASE_DIR / "data" / "answer_cache.json",
        alias="ANSWER_CACHE_FILE",
    )
    live_coding_tasks_file: Path = Field(
        default=BASE_DIR / "data" / "live_coding_tasks.json",
        alias="LIVE_CODING_TASKS_FILE",
    )

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
