"""Database selector. `DB_TYPE` (mysql | postgresql) picks the SQL backend; `DATABASE_URL` overrides it
(sqlite for dev/tests). MongoDB is separate and opt-in via `app.database.mongodb`. Feature code imports
`SessionLocal` / `engine` from here and never builds connections itself."""

from app.core.config import get_settings


def _backend():
    db_type = get_settings().db_type
    if db_type == "postgresql":
        from app.database import postgresql as backend
    else:
        from app.database import mysql as backend
    return backend


_backend = _backend()
engine = _backend.engine
SessionLocal = _backend.SessionLocal

__all__ = ["engine", "SessionLocal"]
