"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the ingestion service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Generic Data Ingestion Service"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "sqlite:///./data/ingestion.db"

    http_timeout_seconds: float = 30.0
    http_max_retries: int = 2
    http_user_agent: str = "GenericDataIngestionService/1.0"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
