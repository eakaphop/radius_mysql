"""Parse/format the FreeRADIUS `Expiration` attribute value.

FreeRADIUS expects e.g. "23 Sep 2026 23:59" (CLAUDE.md section 4.1), in the
server's local time.
"""

from datetime import datetime

from app.utils.timezones import to_server_local_naive

EXPIRATION_FORMAT = "%d %b %Y %H:%M"


class InvalidExpirationError(Exception):
    pass


def format_expiration(value: datetime) -> str:
    """Timezone-aware input (e.g. ISO-8601 with Z from the browser) is converted
    to server-local time first, since that is how FreeRADIUS reads the value."""
    return to_server_local_naive(value).strftime(EXPIRATION_FORMAT)


def parse_expiration(value: str) -> datetime:
    """Parse a stored Expiration value; raises InvalidExpirationError if malformed."""
    try:
        return datetime.strptime(value.strip(), EXPIRATION_FORMAT)
    except ValueError as exc:
        raise InvalidExpirationError(value) from exc


def is_expired(value: str, *, now: datetime | None = None) -> bool:
    """True if the stored Expiration value is in the past. Unparsable values are
    treated as not expired, so a hand-written row can't silently lock a user out."""
    try:
        expires_at = parse_expiration(value)
    except InvalidExpirationError:
        return False
    return expires_at < (now or datetime.now())
