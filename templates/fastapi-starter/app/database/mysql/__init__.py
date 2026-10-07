"""mysql package: config, declarative base and session."""

from app.database.mysql.session import SessionLocal, engine

__all__ = ["SessionLocal", "engine"]
