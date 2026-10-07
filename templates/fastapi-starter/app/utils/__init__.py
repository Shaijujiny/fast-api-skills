"""Shared helpers. Get "now" from here, never scattered datetime.now() calls."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)
