"""Schemas shared across resources."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

from app.utils.radius_attrs import is_valid_operator

T = TypeVar("T")

MAX_PAGE_SIZE = 200


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class AttributeItem(BaseModel):
    """One RADIUS attribute row (radcheck/radreply/radgroup*)."""

    attribute: str = Field(min_length=1, max_length=64)
    op: str = Field(default=":=", max_length=2)
    value: str = Field(max_length=253)

    @field_validator("op")
    @classmethod
    def validate_op(cls, value: str) -> str:
        if not is_valid_operator(value):
            raise ValueError(f"Unsupported RADIUS operator: {value}")
        return value
