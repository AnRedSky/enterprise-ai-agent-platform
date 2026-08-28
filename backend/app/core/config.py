import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _env_files() -> tuple[str, ...]:
    """返回按优先级排列的环境配置文件。"""
    app_env = os.getenv("APP_ENV", "development").strip().lower() or "development"
    files = [
        ".env.example",
        ".env",
        ".env.local",
        f".env.{app_env}",
        f".env.{app_env}.local",
    ]
    explicit = os.getenv("ENV_FILE")
    if explicit:
        explicit_path = Path(explicit)
        files.append(explicit if os.path.isabs(explicit) else str(BACKEND_ROOT / explicit_path))
    return tuple(path if os.path.isabs(path) else str(BACKEND_ROOT / path) for path in files)


class Settings(BaseSettings):
    app_name: str = "Enterprise AI Agent Platform"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    model_provider: str = "mock"
    model_base_url: str | None = None
    model_api_key: str | None = None
    model_default_name: str = "mock-model"
    model_timeout_seconds: float = 60.0
    model_fallback_to_mock: bool = False

    embedding_provider: str = "none"
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str | None = None
    embedding_timeout_seconds: float = 30.0
    embedding_dimension: int = 768
    embedding_batch_size: int = 32
    embedding_dimensions_parameter_enabled: bool = False

    vector_provider: str = "none"
    vector_db_url: str | None = None
    vector_db_collection: str = "knowledge_chunks"
    vector_top_k: int = 5
    vector_min_score: float = 0.0

    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent_platform"
    redis_url: str = "redis://localhost:6379/0"
    scheduler_poll_interval_seconds: float = 5.0

    # Multi-Agent Collaboration 企业治理默认值；生产环境必须通过环境配置显式复核。
    multi_agent_max_delegation_depth: int = 3
    multi_agent_max_active_delegations: int = 4
    multi_agent_timeout_seconds: int = 300
    multi_agent_model_budget: dict = {}

    jwt_secret_key: str = "change-me-in-local-env"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
