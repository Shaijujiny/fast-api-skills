"""All configuration comes from environment variables / .env (blueprint ch. 8)."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "fastapi-starter"
    database_url: str = "sqlite:///./app.db"
    secret_key: SecretStr = Field(min_length=16)  # required, no default
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    cors_origins: list[str] = ["http://localhost:3000"]
    default_language: str = "en"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
