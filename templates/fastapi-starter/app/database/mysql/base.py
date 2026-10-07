"""Declarative base shared by all SQL backends (models live in app/models)."""

from app.models.base import Base, TimestampMixin

__all__ = ["Base", "TimestampMixin"]
