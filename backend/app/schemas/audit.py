"""Pydantic schemas for /audit."""

from typing import Any

from pydantic import BaseModel

from app.utils.timezones import UtcDateTime


class AuditItem(BaseModel):
    id: int
    admin_id: int
    admin_username: str
    action: str
    resource_type: str
    resource_id: str | None
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    ip_address: str | None
    created_at: UtcDateTime
