from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173"
    static_dir: str = "static"
    admin_access_key: str = ""
    database_url: str = "sqlite:///./retrace.db"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout: float = 30.0

    github_webhook_secret: str = ""
    github_token: str = ""
    slack_webhook_url: str = ""

    max_questions: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
