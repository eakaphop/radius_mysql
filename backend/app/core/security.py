"""Password hashing, JWT access tokens, and opaque refresh tokens."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(admin_id: int, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": str(admin_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.app_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Return (raw_token, token_hash, expires_at). Only the hash is stored.

    expires_at is naive UTC (matching the DATETIME column and datetime.utcnow()
    used elsewhere) rather than tz-aware, to avoid naive/aware mismatches.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        days=settings.refresh_token_expire_days
    )
    return raw_token, token_hash, expires_at


def hash_refresh_token(raw_token: str) -> str:
    # Refresh tokens are high-entropy random values, not low-entropy secrets
    # like passwords, so a fast hash (not bcrypt) is appropriate here.
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
