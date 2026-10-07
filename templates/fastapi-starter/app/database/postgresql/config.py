"""postgresql connection settings (env prefix `POSTGRESQL_`). `DATABASE_URL` overrides the built URL."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import get_settings


class PostgresqlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="POSTGRESQL_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "app"
    password: str = ""
    name: str = "app"
    pool_size: int = 5
    max_overflow: int = 10


def get_url() -> str:
    override = get_settings().database_url
    if override:
        return override
    s = PostgresqlSettings()
    return f"postgresql+psycopg://{s.user}:{s.password}@{s.host}:{s.port}/{s.name}"
