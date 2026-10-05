"""Pydantic schemas for /postauth."""

import enum

from pydantic import BaseModel

from app.utils.timezones import RadiusDateTime


class PostAuthReply(str, enum.Enum):
    accept = "Access-Accept"
    reject = "Access-Reject"


class PostAuthItem(BaseModel):
    id: int
    username: str
    reply: str
    authdate: RadiusDateTime

    model_config = {"from_attributes": True}
