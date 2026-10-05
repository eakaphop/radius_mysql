"""NAS client business logic (FreeRADIUS `nas` table).

Secrets are masked everywhere (responses, audit rows) unless explicitly
revealed by an admin (CLAUDE.md section 8).
"""

import ipaddress
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.models.radius import Nas
from app.schemas.nas import MASKED_SECRET, NasOut, NasWrite
from app.services.audit_service import record_audit_log
from app.utils.sql import escape_like

RESOURCE_TYPE = "nas"


class NasNotFoundError(Exception):
    pass


class NasAlreadyExistsError(Exception):
    pass


def _to_out(row: Nas, *, reveal: bool = False) -> NasOut:
    return NasOut(
        id=row.id,
        nasname=row.nasname,
        shortname=row.shortname,
        type=row.type,
        secret=row.secret if reveal else MASKED_SECRET,
        description=row.description,
    )


def _audit_view(
    nasname: str, shortname: str | None, nas_type: str | None, description: str | None
) -> dict[str, Any]:
    return {
        "nasname": nasname,
        "shortname": shortname,
        "type": nas_type,
        "description": description,
        "secret": MASKED_SECRET,
    }


async def list_nas(
    db: AsyncSession, *, search: str | None = None, page: int = 1, page_size: int = 25
) -> tuple[list[NasOut], int]:
    conditions: list[ColumnElement[bool]] = []
    if search:
        pattern = f"%{escape_like(search)}%"
        conditions.append(
            or_(
                Nas.nasname.like(pattern, escape="\\"),
                Nas.shortname.like(pattern, escape="\\"),
                Nas.description.like(pattern, escape="\\"),
            )
        )

    total = await db.scalar(select(func.count()).select_from(Nas).where(*conditions))
    rows = (
        (
            await db.execute(
                select(Nas)
                .where(*conditions)
                .order_by(Nas.nasname)
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        )
        .scalars()
        .all()
    )
    return [_to_out(row) for row in rows], total or 0


async def _get_row(db: AsyncSession, nas_id: int) -> Nas:
    row = await db.get(Nas, nas_id)
    if row is None:
        raise NasNotFoundError(nas_id)
    return row


async def get_nas(db: AsyncSession, nas_id: int, *, reveal: bool = False) -> NasOut:
    return _to_out(await _get_row(db, nas_id), reveal=reveal)


async def _nasname_taken(db: AsyncSession, nasname: str, *, exclude_id: int | None = None) -> bool:
    statement = select(Nas.id).where(Nas.nasname == nasname)
    if exclude_id is not None:
        statement = statement.where(Nas.id != exclude_id)
    return await db.scalar(statement.limit(1)) is not None


async def create_nas(
    db: AsyncSession, payload: NasWrite, *, admin_id: int, ip_address: str | None
) -> NasOut:
    if await _nasname_taken(db, payload.nasname):
        raise NasAlreadyExistsError(payload.nasname)

    row = Nas(
        nasname=payload.nasname,
        shortname=payload.shortname,
        type=payload.type,
        secret=payload.secret,
        description=payload.description,
    )
    db.add(row)
    await db.flush()

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="create",
        resource_type=RESOURCE_TYPE,
        resource_id=str(row.id),
        after=_audit_view(row.nasname, row.shortname, row.type, row.description),
        ip_address=ip_address,
    )
    await db.commit()
    return _to_out(row)


async def update_nas(
    db: AsyncSession, nas_id: int, payload: NasWrite, *, admin_id: int, ip_address: str | None
) -> NasOut:
    row = await _get_row(db, nas_id)
    if await _nasname_taken(db, payload.nasname, exclude_id=nas_id):
        raise NasAlreadyExistsError(payload.nasname)

    before = _audit_view(row.nasname, row.shortname, row.type, row.description)
    before["secret_changed"] = row.secret != payload.secret

    row.nasname = payload.nasname
    row.shortname = payload.shortname
    row.type = payload.type
    row.secret = payload.secret
    row.description = payload.description

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="update",
        resource_type=RESOURCE_TYPE,
        resource_id=str(row.id),
        before=before,
        after=_audit_view(row.nasname, row.shortname, row.type, row.description),
        ip_address=ip_address,
    )
    await db.commit()
    return _to_out(row)


async def delete_nas(
    db: AsyncSession, nas_id: int, *, admin_id: int, ip_address: str | None
) -> None:
    row = await _get_row(db, nas_id)
    before = _audit_view(row.nasname, row.shortname, row.type, row.description)

    await db.delete(row)
    await record_audit_log(
        db,
        admin_id=admin_id,
        action="delete",
        resource_type=RESOURCE_TYPE,
        resource_id=str(nas_id),
        before=before,
        ip_address=ip_address,
    )
    await db.commit()


async def find_secret_for_nas_ip(db: AsyncSession, nas_ip: str) -> str | None:
    """Secret for the NAS that sent a session: exact nasname match first, then
    any nasname that is a CIDR range containing the address."""
    rows = list((await db.execute(select(Nas))).scalars().all())
    for row in rows:
        if row.nasname == nas_ip:
            return row.secret

    try:
        address = ipaddress.ip_address(nas_ip)
    except ValueError:
        return None
    for row in rows:
        try:
            network = ipaddress.ip_network(row.nasname, strict=False)
        except ValueError:
            continue
        if address in network:
            return row.secret
    return None
