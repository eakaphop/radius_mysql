"""POST /auth/login, /auth/refresh, /auth/logout, GET /auth/me, PATCH /auth/me/password.

Refresh token is set as an httpOnly cookie (see CLAUDE.md section 6/7.1).
It is also returned in the login response body as a documented dev fallback
for cross-port (5174 -> 8001) setups where the cookie doesn't round-trip —
see docs/decisions.md. The frontend must not persist that body value.
"""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_admin, get_db
from app.core.errors import ApiError
from app.core.rate_limit import is_rate_limited
from app.db.models.admin_user import AppAdminUser
from app.schemas.auth import AdminOut, LoginRequest, PasswordChangeRequest, TokenResponse
from app.services import auth_service
from app.services.auth_service import InvalidCredentialsError, InvalidRefreshTokenError
from app.utils.request_context import client_ip

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,  # HTTP-only LAN deployment for now (CLAUDE.md section 8)
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    ip_address = client_ip(request)
    if is_rate_limited(f"login:{ip_address}", max_hits=5, window_seconds=60):
        raise ApiError(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            code="RATE_LIMITED",
        )

    try:
        admin = await auth_service.authenticate_admin(db, body.username, body.password)
    except InvalidCredentialsError as exc:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            code="INVALID_CREDENTIALS",
        ) from exc

    access_token, raw_refresh_token = await auth_service.issue_tokens(
        db, admin, ip_address=ip_address
    )
    _set_refresh_cookie(response, raw_refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        admin=AdminOut.model_validate(admin),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh_token is None:
        try:
            body = await request.json()
        except ValueError:
            body = {}
        raw_refresh_token = body.get("refresh_token") if isinstance(body, dict) else None

    if not raw_refresh_token:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
            code="MISSING_REFRESH_TOKEN",
        )

    try:
        admin, access_token, new_raw_refresh_token = await auth_service.rotate_refresh_token(
            db, raw_refresh_token, ip_address=client_ip(request)
        )
    except InvalidRefreshTokenError as exc:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            code="INVALID_REFRESH_TOKEN",
        ) from exc

    _set_refresh_cookie(response, new_raw_refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_raw_refresh_token,
        admin=AdminOut.model_validate(admin),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(get_current_admin),
) -> None:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh_token:
        await auth_service.revoke_refresh_token(
            db, raw_refresh_token, admin_id=admin.id, ip_address=client_ip(request)
        )
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=AdminOut)
async def me(admin: AppAdminUser = Depends(get_current_admin)) -> AdminOut:
    return AdminOut.model_validate(admin)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AppAdminUser = Depends(get_current_admin),
) -> None:
    try:
        await auth_service.change_password(
            db,
            admin,
            current_password=payload.current_password,
            new_password=payload.new_password,
            keep_refresh_token=request.cookies.get(REFRESH_COOKIE_NAME),
            ip_address=client_ip(request),
        )
    except InvalidCredentialsError as exc:
        raise ApiError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
            code="INVALID_CURRENT_PASSWORD",
        ) from exc
