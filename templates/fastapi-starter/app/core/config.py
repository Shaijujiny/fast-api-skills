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
    refresh_token_expire_days: int = 14
    # Rate limiting: in-memory backend by default (single process); set REDIS_URL to share counters.
    redis_url: str | None = None
    login_rate_limit: int = 10  # attempts per window, per IP + email
    login_rate_window_seconds: int = 60
    refresh_rate_limit: int = 30  # per IP
    refresh_rate_window_seconds: int = 60
    # Account lockout after repeated failed logins.
    login_max_failed_attempts: int = 5
    login_lockout_minutes: int = 15
    # How long a role's resolved permissions may be cached in-process.
    permission_cache_ttl_seconds: int = 30
    cors_origins: list[str] = ["http://localhost:3000"]
    default_language: str = "en"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
