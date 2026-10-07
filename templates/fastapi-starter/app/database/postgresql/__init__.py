"""postgresql package: config, declarative base and session."""

from app.database.postgresql.session import SessionLocal, engine

__all__ = ["SessionLocal", "engine"]
