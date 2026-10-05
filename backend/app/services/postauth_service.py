"""radpostauth queries.

The default schema doesn't index authdate, so results are ordered by the
primary key (insertion order == authdate order) — see docs/decisions.md.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.models.radius import RadPostAuth
from app.schemas.postauth import PostAuthItem, PostAuthReply
from app.utils.timezones import to_server_local_naive


async def list_postauth(
    db: AsyncSession,
    *,
    username: str | None = None,
    reply: PostAuthReply | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[PostAuthItem], int]:
    conditions: list[ColumnElement[bool]] = []
    if username:
        conditions.append(RadPostAuth.username == username)
    if reply is not None:
        conditions.append(RadPostAuth.reply == reply.value)
    if date_from:
        conditions.append(RadPostAuth.authdate >= to_server_local_naive(date_from))
    if date_to:
        conditions.append(RadPostAuth.authdate <= to_server_local_naive(date_to))

    total = await db.scalar(select(func.count()).select_from(RadPostAuth).where(*conditions))
    rows = (
        (
            await db.execute(
                select(RadPostAuth)
                .where(*conditions)
                .order_by(RadPostAuth.id.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        )
        .scalars()
        .all()
    )
    return [PostAuthItem.model_validate(row) for row in rows], total or 0
