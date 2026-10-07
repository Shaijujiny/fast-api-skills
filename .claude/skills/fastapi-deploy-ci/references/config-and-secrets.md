# Config and secrets

```python
from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "local"            # local | test | staging | prod
    database_url: SecretStr
    redis_url: SecretStr
    secret_key: SecretStr
    db_pool_size: int = 10
    cors_origins: list[str] = []

@lru_cache
def get_settings() -> Settings:
    return Settings()  # raises at startup if a required var is missing
```

- Use `SecretStr` so secrets do not appear in `repr`, logs or tracebacks; call `.get_secret_value()` only at use.
- Inject with `Depends(get_settings)`; override in tests.
- `.env` is gitignored and dockerignored; `.env.example` lists names with dummy values.
- Per-environment values live in the platform (CI masked/protected variables, secret manager, orchestrator secrets),
  scoped per environment; prod secrets are not readable from staging pipelines.
- Rotate on leak or staff change; support two valid keys during rotation (e.g. JWT signing key id).
- Run a secret scanner (gitleaks in pre-commit and CI). If a secret was committed: rotate first, then purge history.
- Disable `/docs` and `/openapi.json` in prod if the API is not public: `FastAPI(docs_url=None, openapi_url=None)`.
- Never print settings at startup; log only non-secret fields (env, version).
