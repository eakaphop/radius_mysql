"""FastAPI application entrypoint: app instance, middleware, routers."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.session import engine

settings = get_settings()

app = FastAPI(title="RADIUS Manager API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Same {detail, code} shape as every other error, with the field errors kept."""
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "detail": "; ".join(str(error.get("msg", "")) for error in errors),
            "code": "VALIDATION_ERROR",
            "errors": jsonable_encoder(errors),
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Check that the API can reach the MariaDB database."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # noqa: BLE001 - report any connectivity failure as unhealthy
        return {"status": "error", "database": f"unreachable: {exc}"}


app.include_router(api_router, prefix="/api/v1")
