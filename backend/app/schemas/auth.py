"""Pydantic schemas for the /auth endpoints."""

from pydantic import BaseModel, Field

from app.db.models.admin_user import AdminRole
from app.utils.timezones import UtcDateTime


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)


class AdminOut(BaseModel):
    id: int
    username: str
    role: AdminRole
    is_active: bool
    last_login_at: UtcDateTime | None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    admin: AdminOut


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)
