"""radacct queries and CSV export.

radacct is large (CLAUDE.md 4.1): every query is bounded by a time window on
acctstarttime (default: last 30 days) and paginated or streamed.
"""

import csv
import io
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.models.radius import RadAcct
from app.db.session import async_session_factory
from app.schemas.accounting import AccountingDetail, AccountingItem
from app.utils.timezones import to_server_local_naive

DEFAULT_WINDOW = timedelta(days=30)

CSV_COLUMNS: tuple[str, ...] = (
    "radacctid",
    "username",
    "nasipaddress",
    "nasporttype",
    "framedipaddress",
    "callingstationid",
    "acctstarttime",
    "acctstoptime",
    "acctsessiontime",
    "acctinputoctets",
    "acctoutputoctets",
    "acctterminatecause",
)

_CSV_FLUSH_CHARS = 64 * 1024
# Cells starting with these are interpreted as formulas by spreadsheet apps.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class AccountingRecordNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class AccountingFilters:
    username: str | None = None
    nasipaddress: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


def _conditions(filters: AccountingFilters) -> list[ColumnElement[bool]]:
    date_from = (
        to_server_local_naive(filters.date_from)
        if filters.date_from
        else datetime.now() - DEFAULT_WINDOW
    )
    conditions: list[ColumnElement[bool]] = [RadAcct.acctstarttime >= date_from]
    if filters.date_to:
        conditions.append(RadAcct.acctstarttime <= to_server_local_naive(filters.date_to))
    if filters.username:
        conditions.append(RadAcct.username == filters.username)
    if filters.nasipaddress:
        conditions.append(RadAcct.nasipaddress == filters.nasipaddress)
    return conditions


async def list_accounting(
    db: AsyncSession, filters: AccountingFilters, *, page: int = 1, page_size: int = 25
) -> tuple[list[AccountingItem], int]:
    conditions = _conditions(filters)
    total = await db.scalar(select(func.count()).select_from(RadAcct).where(*conditions))
    rows = (
        (
            await db.execute(
                select(RadAcct)
                .where(*conditions)
                .order_by(RadAcct.acctstarttime.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        )
        .scalars()
        .all()
    )
    return [AccountingItem.model_validate(row) for row in rows], total or 0


async def get_accounting(db: AsyncSession, radacctid: int) -> AccountingDetail:
    row = await db.get(RadAcct, radacctid)
    if row is None:
        raise AccountingRecordNotFoundError(radacctid)
    return AccountingDetail.model_validate(row)


def csv_cell(value: object) -> str:
    """Render one CSV cell, neutralising spreadsheet formula injection."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    text = str(value)
    if isinstance(value, str) and text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def _drain(buffer: io.StringIO) -> str:
    chunk = buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    return chunk


async def iter_accounting_csv(filters: AccountingFilters) -> AsyncIterator[str]:
    """Stream matching rows as CSV.

    Opens its own session: FastAPI tears request dependencies down before a
    StreamingResponse body is consumed, so the request's session can't be used.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    buffer.write("\ufeff")  # BOM so spreadsheet apps read UTF-8 (Thai) correctly
    writer.writerow(CSV_COLUMNS)

    async with async_session_factory() as db:
        result = await db.stream_scalars(
            select(RadAcct)
            .where(*_conditions(filters))
            .order_by(RadAcct.acctstarttime.desc())
            .execution_options(yield_per=1000)
        )
        async for row in result:
            writer.writerow([csv_cell(getattr(row, column)) for column in CSV_COLUMNS])
            if buffer.tell() >= _CSV_FLUSH_CHARS:
                yield _drain(buffer)

    yield _drain(buffer)
