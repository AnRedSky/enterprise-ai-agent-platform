import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _env_files() -> tuple[str, ...]:
    """Return environment files from lowest to highest file precedence."""
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
        files.append(
            explicit if os.path.isabs(explicit) else str(BACKEND_ROOT / explicit_path)
        )
    return tuple(
        path if os.path.isabs(path) else str(BACKEND_ROOT / path) for path in files
    )


class Settings(BaseSettings):
    app_name: str = "Enterprise AI Agent Platform"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # Provider type selects an adapter; provider name is deployment metadata and
    # may be any operator-defined value (for example, "company-ollama").
    model_provider: str = "mock"
    model_provider_name: str = "default-chat-provider"
    model_base_url: str | None = None
    model_api_key: str | None = None
    model_default_name: str = "mock-model"
    model_timeout_seconds: float = 60.0
    model_fallback_to_mock: bool = False

    embedding_provider: str = "none"
    embedding_provider_name: str = "default-embedding-provider"
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

    # Retrieval evaluation defaults are application configuration, not runner
    # constants. CLI arguments are explicit per-run overrides.
    retrieval_evaluation_top_k: int = 3
    retrieval_evaluation_min_score: float = 0.0
    retrieval_evaluation_min_recall_at_k: float | None = None
    retrieval_evaluation_min_precision_at_k: float | None = None
    retrieval_evaluation_min_mrr: float | None = None
    retrieval_evaluation_min_citation_correctness: float | None = None
    retrieval_evaluation_max_error_rate: float = 0.0

    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent_platform"
    redis_url: str = "redis://localhost:6379/0"

    scheduler_enabled: bool = True
    scheduler_poll_interval_seconds: float = 5.0

    jwt_secret_key: str = "change-me-in-local-env"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
