"""Pydantic schemas for /dashboard."""

from pydantic import BaseModel

from app.utils.timezones import RadiusDateTime


class DashboardSummary(BaseModel):
    total_users: int
    online_users: int
    online_sessions: int
    auth_accept_24h: int
    auth_reject_24h: int
    traffic_today_download_bytes: int
    traffic_today_upload_bytes: int


class TrafficPoint(BaseModel):
    date: str
    download_bytes: int
    upload_bytes: int


class AuthStatPoint(BaseModel):
    hour: RadiusDateTime
    accept: int
    reject: int
