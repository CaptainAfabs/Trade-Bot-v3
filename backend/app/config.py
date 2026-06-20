from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    alphavantage_api_key: str = ""
    fmp_api_key: str = ""
    resend_api_key: str = ""
    email_to: str = ""
    email_from: str = "onboarding@resend.dev"

    db_path: Path = Path("data/stock_advisor.db")
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    claude_chat_model: str = "claude-sonnet-4-6"
    claude_bulk_model: str = "claude-haiku-4-5-20251001"


settings = Settings()
