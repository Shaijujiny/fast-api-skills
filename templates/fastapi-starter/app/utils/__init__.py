"""Shared helpers. Get "now" from here, never scattered datetime.now() calls."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC so comparisons with utc_now() work everywhere."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
