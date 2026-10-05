"""Timezone handling for values read from and written to the database.

- app_* tables store naive UTC (datetime.utcnow()).
- FreeRADIUS tables store naive server-local time (MariaDB NOW() running on the
  same host as this API — CLAUDE.md section 2).

API responses always carry an explicit UTC offset so the browser can render
them in its own timezone (CLAUDE.md section 6).
"""

from datetime import UTC, datetime, tzinfo
from typing import Annotated

from pydantic import PlainSerializer


def _server_tz() -> tzinfo | None:
    return datetime.now().astimezone().tzinfo


def to_utc_naive(value: datetime) -> datetime:
    """Normalise an input datetime for comparison with app_* columns."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def to_server_local_naive(value: datetime) -> datetime:
    """Normalise an input datetime for comparison with FreeRADIUS columns."""
    if value.tzinfo is None:
        return value
    return value.astimezone().replace(tzinfo=None)


def _serialize_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _serialize_server_local(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=_server_tz())
    return value.isoformat()


UtcDateTime = Annotated[datetime, PlainSerializer(_serialize_utc, return_type=str)]
RadiusDateTime = Annotated[datetime, PlainSerializer(_serialize_server_local, return_type=str)]
