"""Unit tests for the RADIUS helper utils — no database required."""

import base64
import hashlib
from datetime import datetime

import pytest

from app.utils.radius_attrs import (
    is_valid_check_attribute,
    is_valid_operator,
    is_valid_reply_attribute,
)
from app.utils.radius_expiration import (
    InvalidExpirationError,
    format_expiration,
    is_expired,
    parse_expiration,
)
from app.utils.radius_password import (
    UnsupportedPasswordAttributeError,
    build_password_value,
)


def test_operator_whitelist() -> None:
    for op in (":=", "==", "=", "+=", "!=", ">", ">=", "<", "<=", "=~", "!~", "=*", "!*"):
        assert is_valid_operator(op)
    assert not is_valid_operator("<>")
    assert not is_valid_operator("; DROP TABLE radcheck")


def test_attribute_whitelists_are_separate() -> None:
    assert is_valid_check_attribute("Cleartext-Password")
    assert not is_valid_check_attribute("Mikrotik-Rate-Limit")
    assert is_valid_reply_attribute("Mikrotik-Rate-Limit")
    assert not is_valid_reply_attribute("Cleartext-Password")


def test_expiration_format_matches_freeradius() -> None:
    assert format_expiration(datetime(2026, 9, 23, 23, 59)) == "23 Sep 2026 23:59"
    assert parse_expiration("23 Sep 2026 23:59") == datetime(2026, 9, 23, 23, 59)


def test_expiration_roundtrip() -> None:
    value = datetime(2027, 1, 2, 3, 4)
    assert parse_expiration(format_expiration(value)) == value


def test_parse_expiration_rejects_garbage() -> None:
    with pytest.raises(InvalidExpirationError):
        parse_expiration("tomorrow")


def test_is_expired_compares_against_now() -> None:
    now = datetime(2026, 9, 13, 12, 0)
    assert is_expired("01 Jan 2020 00:00", now=now)
    assert not is_expired("01 Jan 2030 00:00", now=now)
    # Unparsable values must not lock a user out.
    assert not is_expired("whenever", now=now)


def test_cleartext_password_is_stored_as_is() -> None:
    assert build_password_value("s3cret", "Cleartext-Password") == "s3cret"


def test_ssha_password_is_salted_sha1() -> None:
    encoded = build_password_value("s3cret", "SSHA-Password")
    decoded = base64.b64decode(encoded)
    digest, salt = decoded[:20], decoded[20:]
    assert len(salt) == 8
    assert hashlib.sha1(b"s3cret" + salt).digest() == digest


def test_ssha_password_uses_a_fresh_salt() -> None:
    assert build_password_value("s3cret", "SSHA-Password") != build_password_value(
        "s3cret", "SSHA-Password"
    )


def test_nt_password_is_uppercase_hex_md4() -> None:
    value = build_password_value("s3cret", "NT-Password")
    assert len(value) == 32
    assert value == value.upper()


def test_unsupported_password_attribute() -> None:
    with pytest.raises(UnsupportedPasswordAttributeError):
        build_password_value("s3cret", "Plaintext-Password")
