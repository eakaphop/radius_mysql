"""/shaping endpoints: bandwidth profiles, preview/parse, apply, effective view."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_db, require_role
from app.core.errors import ApiError
from app.db.models.admin_user import AppAdminUser
from app.schemas.common import MAX_PAGE_SIZE, PaginatedResponse
from app.schemas.shaping import (
    ApplyRequest,
    ApplyResponse,
    EffectiveShapingResponse,
    ParseRequest,
    ParseResponse,
    PreviewResponse,
    ProfileOut,
    ProfileWrite,
    ReapplyResponse,
    ShapingFields,
    TargetOut,
)
from app.services import shaping_service
from app.services.mikrotik_shaping import RateLimitParseError
from app.services.shaping_service import (
    ProfileInUseError,
    ProfileNameExistsError,
    ProfileNotFoundError,
    ProfileServiceMismatchError,
    ShapingTargetNotFoundError,
)
from app.utils.request_context import client_ip

router = APIRouter(prefix="/shaping", tags=["shaping"])


def _profile_not_found(profile_id: int) -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Profile {profile_id} not found",
        code="PROFILE_NOT_FOUND",
    )


def _name_exists(name: str) -> ApiError:
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"A profile named '{name}' already exists",
        code="PROFILE_NAME_EXISTS",
    )


@router.get("/profiles", response_model=PaginatedResponse[ProfileOut])
async def list_profiles(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[ProfileOut]:
    items, total = await shaping_service.list_profiles(
        db, search=search, page=page, page_size=page_size
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/profiles", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileWrite,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> ProfileOut:
    try:
        return await shaping_service.create_profile(
            db, payload, admin_id=admin.id, ip_address=ip_address
        )
    except ProfileNameExistsError as exc:
        raise _name_exists(payload.name) from exc


@router.get("/profiles/{profile_id}", response_model=ProfileOut)
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> ProfileOut:
    try:
        return await shaping_service.get_profile(db, profile_id)
    except ProfileNotFoundError as exc:
        raise _profile_not_found(profile_id) from exc


@router.put("/profiles/{profile_id}", response_model=ProfileOut)
async def update_profile(
    profile_id: int,
    payload: ProfileWrite,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> ProfileOut:
    try:
        return await shaping_service.update_profile(
            db, profile_id, payload, admin_id=admin.id, ip_address=ip_address
        )
    except ProfileNotFoundError as exc:
        raise _profile_not_found(profile_id) from exc
    except ProfileNameExistsError as exc:
        raise _name_exists(payload.name) from exc


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> None:
    try:
        await shaping_service.delete_profile(
            db, profile_id, admin_id=admin.id, ip_address=ip_address
        )
    except ProfileNotFoundError as exc:
        raise _profile_not_found(profile_id) from exc
    except ProfileInUseError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile is still applied to groups or users",
            code="PROFILE_IN_USE",
        ) from exc


@router.post("/preview", response_model=PreviewResponse)
async def preview(
    fields: ShapingFields, _: AppAdminUser = Depends(get_current_admin)
) -> PreviewResponse:
    return shaping_service.preview(fields)


@router.post("/parse", response_model=ParseResponse)
async def parse(
    payload: ParseRequest, _: AppAdminUser = Depends(get_current_admin)
) -> ParseResponse:
    try:
        return shaping_service.parse(payload.rate_limit)
    except RateLimitParseError as exc:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            code="INVALID_RATE_LIMIT",
        ) from exc


@router.post("/profiles/{profile_id}/apply", response_model=ApplyResponse)
async def apply_profile(
    profile_id: int,
    payload: ApplyRequest,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> ApplyResponse:
    try:
        return await shaping_service.apply_profile(
            db,
            profile_id,
            payload.target,
            payload.name,
            admin_id=admin.id,
            ip_address=ip_address,
        )
    except ProfileNotFoundError as exc:
        raise _profile_not_found(profile_id) from exc
    except ShapingTargetNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc), code="TARGET_NOT_FOUND"
        ) from exc
    except ProfileServiceMismatchError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            code="PROFILE_SERVICE_MISMATCH",
        ) from exc


@router.post("/profiles/{profile_id}/reapply", response_model=ReapplyResponse)
async def reapply_profile(
    profile_id: int,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> ReapplyResponse:
    try:
        applied = await shaping_service.reapply_profile(
            db, profile_id, admin_id=admin.id, ip_address=ip_address
        )
    except ProfileNotFoundError as exc:
        raise _profile_not_found(profile_id) from exc
    except ShapingTargetNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc), code="TARGET_NOT_FOUND"
        ) from exc
    except ProfileServiceMismatchError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            code="PROFILE_SERVICE_MISMATCH",
        ) from exc
    return ReapplyResponse(applied=applied)


@router.get("/profiles/{profile_id}/targets", response_model=list[TargetOut])
async def list_targets(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> list[TargetOut]:
    try:
        return await shaping_service.list_targets(db, profile_id)
    except ProfileNotFoundError as exc:
        raise _profile_not_found(profile_id) from exc


@router.get("/users/{username}/effective", response_model=EffectiveShapingResponse)
async def get_effective_shaping(
    username: str,
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> EffectiveShapingResponse:
    try:
        return await shaping_service.get_effective_shaping(db, username)
    except ShapingTargetNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
            code="USER_NOT_FOUND",
        ) from exc
