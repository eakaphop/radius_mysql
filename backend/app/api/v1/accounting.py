"""/accounting endpoints (radacct list, detail, CSV export)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_db
from app.core.errors import ApiError
from app.db.models.admin_user import AppAdminUser
from app.schemas.accounting import AccountingDetail, AccountingItem
from app.schemas.common import MAX_PAGE_SIZE, PaginatedResponse
from app.services import accounting_service
from app.services.accounting_service import AccountingFilters, AccountingRecordNotFoundError

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.get("", response_model=PaginatedResponse[AccountingItem])
async def list_accounting(
    username: str | None = None,
    nasipaddress: str | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[AccountingItem]:
    filters = AccountingFilters(
        username=username, nasipaddress=nasipaddress, date_from=date_from, date_to=date_to
    )
    items, total = await accounting_service.list_accounting(
        db, filters, page=page, page_size=page_size
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


# Declared before /{radacctid} so "export" isn't parsed as an id.
@router.get("/export")
async def export_accounting(
    username: str | None = None,
    nasipaddress: str | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    _: AppAdminUser = Depends(get_current_admin),
) -> StreamingResponse:
    filters = AccountingFilters(
        username=username, nasipaddress=nasipaddress, date_from=date_from, date_to=date_to
    )
    filename = f"accounting-{datetime.now():%Y%m%d-%H%M%S}.csv"
    return StreamingResponse(
        accounting_service.iter_accounting_csv(filters),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{radacctid}", response_model=AccountingDetail)
async def get_accounting(
    radacctid: int,
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> AccountingDetail:
    try:
        return await accounting_service.get_accounting(db, radacctid)
    except AccountingRecordNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accounting record {radacctid} not found",
            code="ACCOUNTING_NOT_FOUND",
        ) from exc
