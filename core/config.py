"""Uygulama yapilandirmasi - .env'den okur."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Tum uygulama ayarlari."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Genel
    app_env: str = "development"
    log_level: str = "INFO"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    use_redis_bus: bool = False

    # PostgreSQL (opsiyonel)
    database_url: str = ""
    use_postgres: bool = False

    # SQLite fallback
    data_dir: str = "data"

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    default_llm_model: str = "openai/gpt-oss-120b"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Ayarlari cache'li sekilde doner."""
    return Settings()