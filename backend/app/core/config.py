from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_provider: str = "mock"
    model_base_url: str | None = None
    model_api_key: str | None = None
    model_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
