"""Business logic for login / refresh / logout / password change. No FastAPI imports.

Note on transactions: AsyncSession "autobegins" a transaction on its first
statement (read or write) and keeps it open until commit()/rollback(). Since
each function here may run a read (e.g. looking up a token) before its
writes on the *same* session the request handler already used, we rely on
that autobegin transaction + a single explicit commit() at the end, rather
than `async with db.begin()` — calling `.begin()` explicitly on a session
that already has an autobegun transaction (from an earlier read in the same
request) raises "A transaction is already begun on this Session". A single
commit() still makes every write in a function atomic, which is what matters
here (CLAUDE.md section 5's "one transaction" requirement).
"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models.admin_user import AppAdminUser
from app.db.models.refresh_token import AppRefreshToken
from app.services.audit_service import record_audit_log


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


async def authenticate_admin(db: AsyncSession, username: str, password: str) -> AppAdminUser:
    result = await db.execute(select(AppAdminUser).where(AppAdminUser.username == username))
    admin = result.scalar_one_or_none()
    if admin is None or not admin.is_active or not verify_password(password, admin.password_hash):
        raise InvalidCredentialsError()
    return admin


async def issue_tokens(
    db: AsyncSession, admin: AppAdminUser, *, ip_address: str | None
) -> tuple[str, str]:
    """Create a new access token + refresh token pair for `admin`.

    Commits the transaction (refresh token row, last_login_at, audit log).
    Returns (access_token, raw_refresh_token).
    """
    raw_refresh_token, token_hash, expires_at = generate_refresh_token()
    db.add(AppRefreshToken(admin_id=admin.id, token_hash=token_hash, expires_at=expires_at))

    admin.last_login_at = datetime.utcnow()

    await record_audit_log(
        db,
        admin_id=admin.id,
        action="login",
        resource_type="auth",
        resource_id=admin.username,
        ip_address=ip_address,
    )
    await db.commit()

    access_token = create_access_token(admin.id, admin.role.value)
    return access_token, raw_refresh_token


async def rotate_refresh_token(
    db: AsyncSession, raw_refresh_token: str, *, ip_address: str | None
) -> tuple[AppAdminUser, str, str]:
    """Validate + revoke the given refresh token, issue a new pair.

    Returns (admin, access_token, new_raw_refresh_token).
    """
    token_hash = hash_refresh_token(raw_refresh_token)
    result = await db.execute(
        select(AppRefreshToken).where(AppRefreshToken.token_hash == token_hash)
    )
    token_row = result.scalar_one_or_none()

    if (
        token_row is None
        or token_row.revoked_at is not None
        or token_row.expires_at < datetime.utcnow()
    ):
        raise InvalidRefreshTokenError()

    admin = await db.get(AppAdminUser, token_row.admin_id)
    if admin is None or not admin.is_active:
        raise InvalidRefreshTokenError()

    token_row.revoked_at = datetime.utcnow()
    new_raw_refresh_token, new_token_hash, new_expires_at = generate_refresh_token()
    db.add(AppRefreshToken(admin_id=admin.id, token_hash=new_token_hash, expires_at=new_expires_at))
    await db.commit()

    access_token = create_access_token(admin.id, admin.role.value)
    return admin, access_token, new_raw_refresh_token


async def revoke_refresh_token(
    db: AsyncSession, raw_refresh_token: str, *, admin_id: int, ip_address: str | None
) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    result = await db.execute(
        select(AppRefreshToken).where(AppRefreshToken.token_hash == token_hash)
    )
    token_row = result.scalar_one_or_none()

    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.utcnow()

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="logout",
        resource_type="auth",
        ip_address=ip_address,
    )
    await db.commit()


async def change_password(
    db: AsyncSession,
    admin: AppAdminUser,
    *,
    current_password: str,
    new_password: str,
    keep_refresh_token: str | None,
    ip_address: str | None,
) -> None:
    """Change the admin's own password and revoke their other sessions.

    The refresh token of the session making the change is kept, so the admin
    isn't logged out of the browser they are using.
    """
    if not verify_password(current_password, admin.password_hash):
        raise InvalidCredentialsError()

    admin.password_hash = hash_password(new_password)

    conditions: list[ColumnElement[bool]] = [
        AppRefreshToken.admin_id == admin.id,
        AppRefreshToken.revoked_at.is_(None),
    ]
    if keep_refresh_token:
        conditions.append(AppRefreshToken.token_hash != hash_refresh_token(keep_refresh_token))
    await db.execute(
        update(AppRefreshToken).where(*conditions).values(revoked_at=datetime.utcnow())
    )

    await record_audit_log(
        db,
        admin_id=admin.id,
        action="password_change",
        resource_type="admin_user",
        resource_id=admin.username,
        after={"password": "***"},
        ip_address=ip_address,
    )
    await db.commit()
