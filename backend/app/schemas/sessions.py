"""Pydantic schemas for /sessions."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.accounting import AccountingItem
from app.utils.timezones import RadiusDateTime


class OnlineSessionItem(AccountingItem):
    service_type: str
    acctupdatetime: RadiusDateTime | None


class SessionCapabilities(BaseModel):
    pod_enabled: bool
    coa_enabled: bool


class CoaRequest(BaseModel):
    profile_id: int | None = None
    rate_limit: str | None = Field(default=None, min_length=1, max_length=253)

    @model_validator(mode="after")
    def exactly_one(self) -> "CoaRequest":
        if (self.profile_id is None) == (self.rate_limit is None):
            raise ValueError("provide exactly one of profile_id or rate_limit")
        return self


class DynAuthResponse(BaseModel):
    success: bool
    response: str | None
    error_cause: str | None
    detail: str
