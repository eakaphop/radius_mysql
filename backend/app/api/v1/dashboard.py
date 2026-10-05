"""/dashboard endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_db
from app.db.models.admin_user import AppAdminUser
from app.schemas.dashboard import AuthStatPoint, DashboardSummary, TrafficPoint
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    db: AsyncSession = Depends(get_db), _: AppAdminUser = Depends(get_current_admin)
) -> DashboardSummary:
    return await dashboard_service.get_summary(db)


@router.get("/traffic", response_model=list[TrafficPoint])
async def traffic(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> list[TrafficPoint]:
    return await dashboard_service.get_traffic(db, days=days)


@router.get("/auth-stats", response_model=list[AuthStatPoint])
async def auth_stats(
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> list[AuthStatPoint]:
    return await dashboard_service.get_auth_stats(db, hours=hours)
