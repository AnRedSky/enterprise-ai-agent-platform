from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise AI Agent Platform"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    model_provider: str = "mock"
    model_base_url: str | None = None
    model_api_key: str | None = None
    model_timeout_seconds: float = 60.0

    embedding_provider: str = "none"
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str | None = None
    embedding_timeout_seconds: float = 30.0

    # Vector retrieval is provider-neutral. Keep `none` until a real Vector DB
    # adapter is selected; the in-memory implementation is test-only.
    vector_provider: str = "none"
    vector_db_url: str | None = None
    vector_db_collection: str = "knowledge_chunks"
    vector_top_k: int = 5
    vector_min_score: float = 0.0

    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent_platform"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-local-env"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
