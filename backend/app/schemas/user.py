"""Pydantic schemas for /users."""

import enum
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import AttributeItem
from app.utils.radius_attrs import is_valid_reply_attribute
from app.utils.timezones import RadiusDateTime


class UserStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"
    expired = "expired"


class ServiceType(str, enum.Enum):
    pppoe = "pppoe"
    hotspot = "hotspot"
    unknown = "unknown"


class ReplyAttributeItem(AttributeItem):
    @field_validator("attribute")
    @classmethod
    def validate_attribute(cls, value: str) -> str:
        if not is_valid_reply_attribute(value):
            raise ValueError(f"Unsupported reply attribute: {value}")
        return value


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=253)
    groups: list[str] = Field(default_factory=list)
    expiration: datetime | None = None
    reply_attributes: list[ReplyAttributeItem] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Replaces group membership, expiration and reply attributes as a set.

    Password and enabled/disabled state have their own PATCH endpoints.
    """

    groups: list[str] = Field(default_factory=list)
    expiration: datetime | None = None
    reply_attributes: list[ReplyAttributeItem] = Field(default_factory=list)


class UserPasswordUpdate(BaseModel):
    password: str = Field(min_length=1, max_length=253)


class UserStatusUpdate(BaseModel):
    enabled: bool


class UserListItem(BaseModel):
    username: str
    status: UserStatus
    has_password: bool
    groups: list[str]
    service_type: ServiceType
    expiration: RadiusDateTime | None


class UserDetail(UserListItem):
    check_attributes: list[AttributeItem]
    reply_attributes: list[AttributeItem]
