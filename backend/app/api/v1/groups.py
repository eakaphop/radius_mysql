"""/groups endpoints. Thin routing only — logic lives in services/group_service."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_db, require_role
from app.core.errors import ApiError
from app.db.models.admin_user import AppAdminUser
from app.schemas.common import MAX_PAGE_SIZE, PaginatedResponse
from app.schemas.group import (
    GroupCreate,
    GroupDetail,
    GroupListItem,
    GroupMember,
    GroupUpdate,
)
from app.services import group_service
from app.services.group_service import GroupAlreadyExistsError, GroupNotFoundError
from app.utils.request_context import client_ip

router = APIRouter(prefix="/groups", tags=["groups"])


def _not_found(groupname: str) -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Group '{groupname}' not found",
        code="GROUP_NOT_FOUND",
    )


@router.get("", response_model=PaginatedResponse[GroupListItem])
async def list_groups(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[GroupListItem]:
    items, total = await group_service.list_groups(
        db, search=search, page=page, page_size=page_size
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{groupname}", response_model=GroupDetail)
async def get_group(
    groupname: str,
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> GroupDetail:
    try:
        return await group_service.get_group(db, groupname)
    except GroupNotFoundError as exc:
        raise _not_found(groupname) from exc


@router.post("", response_model=GroupDetail, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> GroupDetail:
    try:
        return await group_service.create_group(
            db, payload, admin_id=admin.id, ip_address=ip_address
        )
    except GroupAlreadyExistsError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Group '{payload.groupname}' already exists",
            code="GROUP_ALREADY_EXISTS",
        ) from exc


@router.put("/{groupname}", response_model=GroupDetail)
async def update_group(
    groupname: str,
    payload: GroupUpdate,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> GroupDetail:
    try:
        return await group_service.update_group(
            db, groupname, payload, admin_id=admin.id, ip_address=ip_address
        )
    except GroupNotFoundError as exc:
        raise _not_found(groupname) from exc


@router.delete("/{groupname}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    groupname: str,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> None:
    try:
        await group_service.delete_group(db, groupname, admin_id=admin.id, ip_address=ip_address)
    except GroupNotFoundError as exc:
        raise _not_found(groupname) from exc


@router.get("/{groupname}/members", response_model=PaginatedResponse[GroupMember])
async def list_group_members(
    groupname: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[GroupMember]:
    items, total = await group_service.list_group_members(
        db, groupname, page=page, page_size=page_size
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
