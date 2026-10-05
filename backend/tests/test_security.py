"""Unit tests for app.core.security — no database required."""

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_password_hash_uses_bcrypt() -> None:
    assert hash_password("something").startswith("$2b$12$")


def test_access_token_roundtrip() -> None:
    token = create_access_token(admin_id=42, role="admin")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_decode_access_token_rejects_garbage() -> None:
    assert decode_access_token("not-a-real-token") is None


def test_generate_refresh_token_hash_matches() -> None:
    raw_token, token_hash, expires_at = generate_refresh_token()
    assert hash_refresh_token(raw_token) == token_hash
    assert expires_at.tzinfo is None
