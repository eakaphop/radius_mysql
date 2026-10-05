"""Pydantic schemas for /groups."""

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import AttributeItem
from app.utils.radius_attrs import is_valid_check_attribute, is_valid_reply_attribute


class GroupCheckAttributeItem(AttributeItem):
    @field_validator("attribute")
    @classmethod
    def validate_attribute(cls, value: str) -> str:
        if not is_valid_check_attribute(value):
            raise ValueError(f"Unsupported check attribute: {value}")
        return value


class GroupReplyAttributeItem(AttributeItem):
    @field_validator("attribute")
    @classmethod
    def validate_attribute(cls, value: str) -> str:
        if not is_valid_reply_attribute(value):
            raise ValueError(f"Unsupported reply attribute: {value}")
        return value


class GroupCreate(BaseModel):
    groupname: str = Field(min_length=1, max_length=64)
    check_attributes: list[GroupCheckAttributeItem] = Field(default_factory=list)
    reply_attributes: list[GroupReplyAttributeItem] = Field(default_factory=list)


class GroupUpdate(BaseModel):
    check_attributes: list[GroupCheckAttributeItem] = Field(default_factory=list)
    reply_attributes: list[GroupReplyAttributeItem] = Field(default_factory=list)


class GroupListItem(BaseModel):
    groupname: str
    member_count: int


class GroupDetail(BaseModel):
    groupname: str
    member_count: int
    check_attributes: list[AttributeItem]
    reply_attributes: list[AttributeItem]


class GroupMember(BaseModel):
    username: str
    priority: int
