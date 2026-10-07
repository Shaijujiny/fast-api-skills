from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MONGODB_", extra="ignore")

    url: str = "mongodb://localhost:27017"
    name: str = "app"
