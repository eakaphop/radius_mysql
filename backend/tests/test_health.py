"""Smoke test for GET /health.

Requires a reachable MariaDB (real target DB, or docker-compose.dev.yml) since
the endpoint reports actual database connectivity rather than a fixed value.
"""

import httpx
import pytest
from httpx import ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_status() -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "error"}
    assert "database" in body
