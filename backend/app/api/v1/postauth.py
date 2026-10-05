"""/postauth endpoint (radpostauth log)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_db
from app.db.models.admin_user import AppAdminUser
from app.schemas.common import MAX_PAGE_SIZE, PaginatedResponse
from app.schemas.postauth import PostAuthItem, PostAuthReply
from app.services import postauth_service

router = APIRouter(prefix="/postauth", tags=["postauth"])


@router.get("", response_model=PaginatedResponse[PostAuthItem])
async def list_postauth(
    username: str | None = None,
    reply: PostAuthReply | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _: AppAdminUser = Depends(get_current_admin),
) -> PaginatedResponse[PostAuthItem]:
    items, total = await postauth_service.list_postauth(
        db,
        username=username,
        reply=reply,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
