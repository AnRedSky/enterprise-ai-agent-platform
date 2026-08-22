import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _env_files() -> tuple[str, ...]:
    """Return environment files from lowest to highest file precedence.

    `.env.example` is the lowest-precedence fallback so a fresh checkout can
    start without creating a local `.env`. It is intentionally a safe,
    non-secret configuration template. Real `.env` files and environment-
    specific overrides take precedence, and process environment variables
    always have the highest precedence.

    `APP_ENV` may be supplied by the process environment to select an
    environment-specific file; otherwise development is used as the default.
    `ENV_FILE` can explicitly add a deployment-specific file without changing
    the application code. Absolute explicit paths are preserved verbatim so
    Unix container paths such as `/run/secrets/agent.env` remain portable when
    configuration selection is tested on Windows.
    """
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
            explicit
            if os.path.isabs(explicit)
            else str(BACKEND_ROOT / explicit_path)
        )
    return tuple(
        path if os.path.isabs(path) else str(BACKEND_ROOT / path)
        for path in files
    )


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

    # `mock` is a deterministic offline fixture for local retrieval validation;
    # it does not represent real model semantic quality.
    embedding_provider: str = "none"
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str | None = None
    embedding_timeout_seconds: float = 30.0
    embedding_dimension: int = 1536
    embedding_batch_size: int = 32
    # Some OpenAI-compatible local providers (for example Ollama-backed
    # Matryoshka embedding models) accept an explicit output dimension. Keep
    # this opt-in because not every OpenAI-compatible provider implements it.
    embedding_dimensions_parameter_enabled: bool = False

    # Vector retrieval is provider-neutral. Keep `none` until PostgreSQL + pgvector
    # is enabled locally; the in-memory implementation remains test-only.
    vector_provider: str = "none"
    vector_db_url: str | None = None
    vector_db_collection: str = "knowledge_chunks"
    vector_top_k: int = 5
    vector_min_score: float = 0.0

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
