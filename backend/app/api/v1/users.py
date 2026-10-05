"""/users endpoints. Thin routing only — logic lives in services/user_service."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_db, require_role
from app.core.errors import ApiError
from app.db.models.admin_user import AppAdminUser
from app.schemas.accounting import AccountingItem
from app.schemas.common import MAX_PAGE_SIZE, PaginatedResponse
from app.schemas.user import (
    UserCreate,
    UserDetail,
    UserListItem,
    UserPasswordUpdate,
    UserStatus,
    UserStatusUpdate,
    UserUpdate,
)
from app.services import user_service
from app.services.user_service import UserAlreadyExistsError, UserNotFoundError
from app.utils.request_context import client_ip

router = APIRouter(prefix="/users", tags=["users"])


def _not_found(username: str) -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User '{username}' not found",
        code="USER_NOT_FOUND",
    )


@router.get("", response_model=PaginatedResponse[UserListItem])
async def list_users(
    search: str | None = None,
    group: str | None = None,
    user_status: UserStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    sort: str = "username",
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[UserListItem]:
    items, total = await user_service.list_users(
        db,
        search=search,
        group=group,
        status=user_status,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{username}", response_model=UserDetail)
async def get_user(
    username: str,
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> UserDetail:
    try:
        return await user_service.get_user(db, username)
    except UserNotFoundError as exc:
        raise _not_found(username) from exc


@router.post("", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> UserDetail:
    try:
        return await user_service.create_user(
            db, payload, admin_id=admin.id, ip_address=ip_address
        )
    except UserAlreadyExistsError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{payload.username}' already exists",
            code="USER_ALREADY_EXISTS",
        ) from exc


@router.put("/{username}", response_model=UserDetail)
async def update_user(
    username: str,
    payload: UserUpdate,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> UserDetail:
    try:
        return await user_service.update_user(
            db, username, payload, admin_id=admin.id, ip_address=ip_address
        )
    except UserNotFoundError as exc:
        raise _not_found(username) from exc


@router.patch("/{username}/password", status_code=status.HTTP_204_NO_CONTENT)
async def set_password(
    username: str,
    payload: UserPasswordUpdate,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> None:
    try:
        await user_service.set_password(
            db, username, payload.password, admin_id=admin.id, ip_address=ip_address
        )
    except UserNotFoundError as exc:
        raise _not_found(username) from exc


@router.patch("/{username}/status", response_model=UserDetail)
async def set_status(
    username: str,
    payload: UserStatusUpdate,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> UserDetail:
    try:
        return await user_service.set_status(
            db, username, payload.enabled, admin_id=admin.id, ip_address=ip_address
        )
    except UserNotFoundError as exc:
        raise _not_found(username) from exc


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    username: str,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> None:
    try:
        await user_service.delete_user(db, username, admin_id=admin.id, ip_address=ip_address)
    except UserNotFoundError as exc:
        raise _not_found(username) from exc


@router.get("/{username}/sessions", response_model=PaginatedResponse[AccountingItem])
async def list_user_sessions(
    username: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[AccountingItem]:
    try:
        items, total = await user_service.list_user_sessions(
            db, username, page=page, page_size=page_size
        )
    except UserNotFoundError as exc:
        raise _not_found(username) from exc
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
