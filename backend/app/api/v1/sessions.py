"""/sessions endpoints: online sessions, Disconnect (PoD) and CoA."""

from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    get_current_admin,
    get_db,
    require_coa_enabled,
    require_pod_enabled,
    require_role,
)
from app.core.errors import ApiError
from app.db.models.admin_user import AppAdminUser
from app.schemas.common import MAX_PAGE_SIZE, PaginatedResponse
from app.schemas.sessions import (
    CoaRequest,
    DynAuthResponse,
    OnlineSessionItem,
    SessionCapabilities,
)
from app.services import sessions_service
from app.services.radclient import DynAuthResult
from app.services.sessions_service import (
    InvalidCoaRequestError,
    NasSecretNotFoundError,
    SessionNotFoundError,
    SessionNotOnlineError,
)
from app.services.shaping_service import ProfileNotFoundError
from app.utils.request_context import client_ip

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _to_response(result: DynAuthResult) -> DynAuthResponse:
    return DynAuthResponse(
        success=result.success,
        response=result.response,
        error_cause=result.error_cause,
        detail=result.detail,
    )


def _session_error(exc: Exception, radacctid: int) -> ApiError:
    if isinstance(exc, SessionNotFoundError):
        return ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {radacctid} not found",
            code="SESSION_NOT_FOUND",
        )
    if isinstance(exc, SessionNotOnlineError):
        return ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session {radacctid} is no longer online",
            code="SESSION_NOT_ONLINE",
        )
    return ApiError(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"No NAS entry with a secret matches {exc}",
        code="NAS_NOT_FOUND",
    )


@router.get("/capabilities", response_model=SessionCapabilities)
async def capabilities(_: AppAdminUser = Depends(get_current_admin)) -> SessionCapabilities:
    """Lets the UI hide Disconnect / Change speed when the feature flags are off."""
    return sessions_service.get_capabilities()


@router.get("/online", response_model=PaginatedResponse[OnlineSessionItem])
async def list_online_sessions(
    service: Literal["all", "pppoe", "hotspot"] = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[OnlineSessionItem]:
    items, total = await sessions_service.list_online_sessions(
        db, service=service, page=page, page_size=page_size
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/{radacctid}/disconnect",
    response_model=DynAuthResponse,
    dependencies=[Depends(require_pod_enabled)],
)
async def disconnect_session(
    radacctid: int,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> DynAuthResponse:
    try:
        result = await sessions_service.disconnect_session(
            db, radacctid, admin_id=admin.id, ip_address=ip_address
        )
    except (SessionNotFoundError, SessionNotOnlineError, NasSecretNotFoundError) as exc:
        raise _session_error(exc, radacctid) from exc
    return _to_response(result)


@router.post(
    "/{radacctid}/coa",
    response_model=DynAuthResponse,
    dependencies=[Depends(require_coa_enabled)],
)
async def change_session_speed(
    radacctid: int,
    payload: CoaRequest,
    ip_address: str | None = Depends(client_ip),
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(require_role("admin")),
) -> DynAuthResponse:
    try:
        result = await sessions_service.change_session_speed(
            db,
            radacctid,
            profile_id=payload.profile_id,
            rate_limit=payload.rate_limit,
            admin_id=admin.id,
            ip_address=ip_address,
        )
    except (SessionNotFoundError, SessionNotOnlineError, NasSecretNotFoundError) as exc:
        raise _session_error(exc, radacctid) from exc
    except ProfileNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {payload.profile_id} not found",
            code="PROFILE_NOT_FOUND",
        ) from exc
    except InvalidCoaRequestError as exc:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            code="INVALID_COA_REQUEST",
        ) from exc
    return _to_response(result)
