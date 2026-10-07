"""Document models: Pydantic classes mapped to a collection."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Document(BaseModel):
    collection: str = ""  # override in subclasses (ClassVar-style default)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
