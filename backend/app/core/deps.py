"""Shared FastAPI dependencies: DB session, current admin, role and feature checks."""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.db.models.admin_user import AdminRole, AppAdminUser
from app.db.session import get_db

__all__ = [
    "get_db",
    "get_current_admin",
    "require_role",
    "require_reveal_permission",
    "require_pod_enabled",
    "require_coa_enabled",
]

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AppAdminUser:
    unauthorized = ApiError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        code="UNAUTHORIZED",
    )
    unauthorized.headers = {"WWW-Authenticate": "Bearer"}
    if credentials is None:
        raise unauthorized

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise unauthorized

    admin_id = payload.get("sub")
    if admin_id is None:
        raise unauthorized

    admin = await db.get(AppAdminUser, int(admin_id))
    if admin is None or not admin.is_active:
        raise unauthorized

    return admin


def require_role(*roles: str) -> Callable[..., Coroutine[Any, Any, AppAdminUser]]:
    async def dependency(admin: AppAdminUser = Depends(get_current_admin)) -> AppAdminUser:
        if admin.role.value not in roles:
            raise ApiError(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this action",
                code="FORBIDDEN",
            )
        return admin

    return dependency


async def require_reveal_permission(
    reveal: bool = Query(default=False),
    admin: AppAdminUser = Depends(get_current_admin),
) -> bool:
    """`?reveal=true` (unmasked NAS secret) is admin-only (CLAUDE.md section 8)."""
    if reveal and admin.role is not AdminRole.admin:
        raise ApiError(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reveal secrets",
            code="FORBIDDEN",
        )
    return reveal


async def require_pod_enabled() -> None:
    if not get_settings().enable_pod:
        raise ApiError(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Disconnect (PoD) is disabled — set ENABLE_POD=true",
            code="POD_DISABLED",
        )


async def require_coa_enabled() -> None:
    if not get_settings().enable_coa:
        raise ApiError(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="CoA is disabled — set ENABLE_COA=true",
            code="COA_DISABLED",
        )
