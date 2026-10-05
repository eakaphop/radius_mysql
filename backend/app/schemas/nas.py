"""Pydantic schemas for /nas."""

import ipaddress
import re

from pydantic import BaseModel, Field, field_validator

MASKED_SECRET = "***"
RELOAD_WARNING = "FreeRADIUS reload required"

_HOSTNAME = re.compile(r"^[A-Za-z0-9.-]{1,128}$")
_NAS_TYPE = re.compile(r"^[A-Za-z0-9_-]{1,30}$")


class NasWrite(BaseModel):
    nasname: str = Field(min_length=1, max_length=128)
    shortname: str | None = Field(default=None, max_length=32)
    type: str = Field(default="other")
    secret: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=200)

    @field_validator("nasname")
    @classmethod
    def validate_nasname(cls, value: str) -> str:
        """An IP address, a CIDR range, or a hostname."""
        try:
            ipaddress.ip_network(value, strict=False)
            return value
        except ValueError:
            pass
        if not _HOSTNAME.match(value):
            raise ValueError("nasname must be an IP address, CIDR range or hostname")
        return value

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if not _NAS_TYPE.match(value):
            raise ValueError("type must match ^[A-Za-z0-9_-]{1,30}$")
        return value

    @field_validator("secret")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
            raise ValueError("secret must not contain control characters")
        return value


class NasOut(BaseModel):
    id: int
    nasname: str
    shortname: str | None
    type: str | None
    secret: str
    description: str | None


class NasWriteResponse(NasOut):
    warning: str = RELOAD_WARNING


class NasDeleteResponse(BaseModel):
    warning: str = RELOAD_WARNING
