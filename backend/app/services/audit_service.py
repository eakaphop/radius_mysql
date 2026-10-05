"""app_audit_log writes and queries.

record_audit_log() must be called within the same transaction as the write it
records (CLAUDE.md section 5) — i.e. before that function's single commit().
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.models.admin_user import AppAdminUser
from app.db.models.audit_log import AppAuditLog
from app.schemas.audit import AuditItem
from app.utils.timezones import to_utc_naive


async def record_audit_log(
    db: AsyncSession,
    *,
    admin_id: int,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AppAuditLog(
            admin_id=admin_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_json=before,
            after_json=after,
            ip_address=ip_address,
        )
    )


@dataclass(frozen=True)
class AuditFilters:
    admin_username: str | None = None
    resource_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


def _conditions(filters: AuditFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.admin_username:
        conditions.append(AppAdminUser.username == filters.admin_username)
    if filters.resource_type:
        conditions.append(AppAuditLog.resource_type == filters.resource_type)
    if filters.date_from:
        conditions.append(AppAuditLog.created_at >= to_utc_naive(filters.date_from))
    if filters.date_to:
        conditions.append(AppAuditLog.created_at <= to_utc_naive(filters.date_to))
    return conditions


async def list_audit_logs(
    db: AsyncSession, filters: AuditFilters, *, page: int = 1, page_size: int = 25
) -> tuple[list[AuditItem], int]:
    conditions = _conditions(filters)
    joined = select(AppAuditLog, AppAdminUser.username).join(
        AppAdminUser, AppAdminUser.id == AppAuditLog.admin_id
    )

    total = await db.scalar(
        select(func.count())
        .select_from(AppAuditLog)
        .join(AppAdminUser, AppAdminUser.id == AppAuditLog.admin_id)
        .where(*conditions)
    )
    rows = (
        await db.execute(
            joined.where(*conditions)
            .order_by(AppAuditLog.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).all()

    items = [
        AuditItem(
            id=log.id,
            admin_id=log.admin_id,
            admin_username=username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            before_json=log.before_json,
            after_json=log.after_json,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log, username in rows
    ]
    return items, total or 0
