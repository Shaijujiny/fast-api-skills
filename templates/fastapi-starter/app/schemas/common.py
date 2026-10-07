"""Shared DTOs: BaseSchema, ApiResponse[T], pagination (blueprint ch. 4.6, 5).

Money rule: money fields are `Decimal` (DB: Numeric(18, 2)), never `float`.
"""

from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class BaseSchema(BaseModel):
    """All DTOs extend this: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, alias_generator=to_camel, str_strip_whitespace=True
    )


class ApiResponse(BaseSchema, Generic[T]):
    status: str = "1"  # "1" success, "0" error
    status_code: int = 200
    code: str = "SUCCESS"
    message: str = ""
    data: T | None = None


class PageParams(BaseSchema):
    offset: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)
    search: str | None = Field(None, max_length=100)


PageQuery = Annotated[PageParams, Query()]


class PageData(BaseSchema, Generic[T]):
    items: list[T]
    total_count: int
