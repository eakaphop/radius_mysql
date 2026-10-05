"""Request-scoped helpers usable as FastAPI dependencies."""

from fastapi import Request


def client_ip(request: Request) -> str | None:
    """Caller IP for audit rows."""
    return request.client.host if request.client else None
