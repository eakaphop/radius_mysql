"""/nas endpoints. Every write response carries the FreeRADIUS reload warning."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_db, require_reveal_permission, require_role
from app.core.errors import ApiError
from app.db.models.admin_user import AppAdminUser
from app.schemas.common import MAX_PAGE_SIZE, PaginatedResponse
from app.schemas.nas import NasDeleteResponse, NasOut, NasWrite, NasWriteResponse
from app.services import nas_service
from app.services.nas_service import NasAlreadyExistsError, NasNotFoundError
from app.utils.request_context import client_ip

router = APIRouter(prefix="/nas", tags=["nas"])


def _not_found(nas_id: int) -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"NAS {nas_id} not found",
        code="NAS_NOT_FOUND",
    )


def _already_exists(nasname: str) -> ApiError:
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"A NAS with nasname '{nasname}' already exists",
        code="NAS_ALREADY_EXISTS",
    )


@router.get("", response_model=PaginatedResponse[NasOut])
async def list_nas(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[NasOut]:
    items, total = await nas_service.list_nas(db, search=search, page=page, page_size=page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{nas_id}", response_model=NasOut)
async def get_nas(
    nas_id: int,
    reveal: bool = Depends(require_reveal_permission),
    db: AsyncSession = Depends(get_db),
) -> NasOut:
    try:
        return await nas_service.get_nas(db, nas_id, reveal=reveal)
    except NasNotFoundError as exc:
        raise _not_found(nas_id) from exc


@router.post("", response_model=NasWriteResponse, status_code=status.HTTP_201_CREATED)
async def create_nas(
    payload: NasWrite,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> NasWriteResponse:
    try:
        nas = await nas_service.create_nas(db, payload, admin_id=admin.id, ip_address=ip_address)
    except NasAlreadyExistsError as exc:
        raise _already_exists(payload.nasname) from exc
    return NasWriteResponse(**nas.model_dump())


@router.put("/{nas_id}", response_model=NasWriteResponse)
async def update_nas(
    nas_id: int,
    payload: NasWrite,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> NasWriteResponse:
    try:
        nas = await nas_service.update_nas(
            db, nas_id, payload, admin_id=admin.id, ip_address=ip_address
        )
    except NasNotFoundError as exc:
        raise _not_found(nas_id) from exc
    except NasAlreadyExistsError as exc:
        raise _already_exists(payload.nasname) from exc
    return NasWriteResponse(**nas.model_dump())


@router.delete("/{nas_id}", response_model=NasDeleteResponse)
async def delete_nas(
    nas_id: int,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> NasDeleteResponse:
    try:
        await nas_service.delete_nas(db, nas_id, admin_id=admin.id, ip_address=ip_address)
    except NasNotFoundError as exc:
        raise _not_found(nas_id) from exc
    return NasDeleteResponse()
