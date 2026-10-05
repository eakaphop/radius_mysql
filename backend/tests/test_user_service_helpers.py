"""Unit tests for user status / service type derivation — no database required."""

from app.db.models.radius import RadCheck
from app.schemas.user import UserStatus
from app.services.user_service import _status_from_rows
from app.utils.service_type import service_type_from_groups
from app.utils.sql import escape_like


def _check(attribute: str, value: str) -> RadCheck:
    return RadCheck(username="bob", attribute=attribute, op=":=", value=value)


def test_status_active_when_only_password_present() -> None:
    assert _status_from_rows([_check("Cleartext-Password", "s3cret")]) is UserStatus.active


def test_status_disabled_when_auth_type_reject_present() -> None:
    rows = [_check("Cleartext-Password", "s3cret"), _check("Auth-Type", "Reject")]
    assert _status_from_rows(rows) is UserStatus.disabled


def test_status_expired_when_expiration_in_the_past() -> None:
    rows = [_check("Cleartext-Password", "s3cret"), _check("Expiration", "01 Jan 2020 00:00")]
    assert _status_from_rows(rows) is UserStatus.expired


def test_status_disabled_wins_over_expired() -> None:
    rows = [
        _check("Expiration", "01 Jan 2020 00:00"),
        _check("Auth-Type", "Reject"),
    ]
    assert _status_from_rows(rows) is UserStatus.disabled


def test_future_expiration_is_active() -> None:
    assert _status_from_rows([_check("Expiration", "01 Jan 2099 00:00")]) is UserStatus.active


def test_service_type_from_group_naming_convention() -> None:
    assert service_type_from_groups(["pppoe-standard"]) == "pppoe"
    assert service_type_from_groups(["hotspot-basic"]) == "hotspot"
    assert service_type_from_groups(["staff"]) == "unknown"
    assert service_type_from_groups([]) == "unknown"


def test_escape_like_neutralises_wildcards() -> None:
    assert escape_like("100%_off") == "100\\%\\_off"
    assert escape_like("back\\slash") == "back\\\\slash"
