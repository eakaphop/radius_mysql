"""Pydantic schemas for /shaping.

Validation rules are not duplicated here: ShapingFields delegates to
services/mikrotik_shaping.validate_fields (single source of truth).
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.db.models.bandwidth_profile import ProfileServiceType
from app.schemas.common import AttributeItem
from app.services.mikrotik_shaping import MAX_QUOTA_BYTES, validate_fields
from app.utils.timezones import UtcDateTime


class ProfileFieldsData(BaseModel):
    """Plain shaping fields, no cross-field validation (used for output)."""

    service_type: ProfileServiceType = ProfileServiceType.both
    download_kbps: int | None = Field(default=None, ge=1)
    upload_kbps: int | None = Field(default=None, ge=1)
    burst_download_kbps: int | None = Field(default=None, ge=1)
    burst_upload_kbps: int | None = Field(default=None, ge=1)
    burst_threshold_download_kbps: int | None = Field(default=None, ge=1)
    burst_threshold_upload_kbps: int | None = Field(default=None, ge=1)
    burst_time_sec: int | None = Field(default=None, ge=1)
    priority: int = Field(default=8, ge=1, le=8)
    min_download_kbps: int | None = Field(default=None, ge=1)
    min_upload_kbps: int | None = Field(default=None, ge=1)
    session_timeout_sec: int | None = Field(default=None, ge=1)
    idle_timeout_sec: int | None = Field(default=None, ge=1)
    simultaneous_use: int | None = Field(default=None, ge=1)
    mikrotik_group: str | None = Field(default=None, max_length=64)
    framed_pool: str | None = Field(default=None, max_length=64)
    total_quota_bytes: int | None = Field(default=None, ge=1, le=MAX_QUOTA_BYTES)
    address_list: str | None = Field(default=None, max_length=64)
    unifi_filter_id: str | None = Field(default=None, max_length=64)


class ShapingFields(ProfileFieldsData):
    @model_validator(mode="after")
    def validate_shaping(self) -> "ShapingFields":
        errors = validate_fields(self.model_dump())
        if errors:
            raise ValueError("; ".join(errors))
        return self


class ProfileWrite(ShapingFields):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class ProfileOut(ProfileFieldsData):
    id: int
    name: str
    description: str | None
    is_active: bool
    rate_limit_string: str | None
    target_count: int
    created_at: UtcDateTime
    updated_at: UtcDateTime


class PreviewResponse(BaseModel):
    attributes: list[AttributeItem]
    check_attributes: list[AttributeItem]
    rate_limit_string: str | None


class ParseRequest(BaseModel):
    rate_limit: str = Field(min_length=1, max_length=253)


class ParseResponse(BaseModel):
    download_kbps: int
    upload_kbps: int
    burst_download_kbps: int | None
    burst_upload_kbps: int | None
    burst_threshold_download_kbps: int | None
    burst_threshold_upload_kbps: int | None
    burst_time_sec: int | None
    priority: int
    min_download_kbps: int | None
    min_upload_kbps: int | None


class ApplyRequest(BaseModel):
    target: Literal["group", "user"]
    name: str = Field(min_length=1, max_length=64)


class ApplyResponse(BaseModel):
    target: Literal["group", "user"]
    name: str
    attributes: list[AttributeItem]
    check_attributes: list[AttributeItem]


class TargetOut(BaseModel):
    target_type: str
    target_name: str
    applied_at: UtcDateTime


class ReapplyResponse(BaseModel):
    applied: list[TargetOut]


class EffectiveAttribute(BaseModel):
    attribute: str
    op: str
    value: str
    source: str


class AssignedProfile(BaseModel):
    profile_id: int
    profile_name: str
    target_type: str
    target_name: str


class EffectiveShapingResponse(BaseModel):
    username: str
    groups: list[str]
    profiles: list[AssignedProfile]
    user_attributes: list[AttributeItem]
    group_attributes: dict[str, list[AttributeItem]]
    effective: list[EffectiveAttribute]
    warnings: list[str]
