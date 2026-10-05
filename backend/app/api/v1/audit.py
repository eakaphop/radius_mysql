"""/audit endpoint (app_audit_log)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_db
from app.db.models.admin_user import AppAdminUser
from app.schemas.audit import AuditItem
from app.schemas.common import MAX_PAGE_SIZE, PaginatedResponse
from app.services.audit_service import AuditFilters, list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditItem])
async def list_audit(
    admin: str | None = None,
    resource_type: str | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[AuditItem]:
    filters = AuditFilters(
        admin_username=admin,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
    )
    items, total = await list_audit_logs(db, filters, page=page, page_size=page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
