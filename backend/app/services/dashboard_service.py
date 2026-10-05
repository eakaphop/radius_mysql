"""Dashboard aggregates.

Times are server-local (FreeRADIUS writes NOW() on this host). Traffic is
attributed to the day a session STARTED; long sessions spanning midnight are
not split across days (see docs/decisions.md).

GROUP BY expressions deliberately take no bound parameters (DATE()/HOUR(),
not DATE_FORMAT(x, %s)), so they stay valid under ONLY_FULL_GROUP_BY.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.radius import RadAcct, RadCheck, RadPostAuth
from app.schemas.dashboard import AuthStatPoint, DashboardSummary, TrafficPoint

ACCEPT = "Access-Accept"
REJECT = "Access-Reject"


async def get_summary(db: AsyncSession) -> DashboardSummary:
    total_users = await db.scalar(select(func.count(distinct(RadCheck.username))))

    online_users, online_sessions = (
        await db.execute(
            select(func.count(distinct(RadAcct.username)), func.count()).where(
                RadAcct.acctstoptime.is_(None)
            )
        )
    ).one()

    since = datetime.now() - timedelta(hours=24)
    auth_counts = {
        reply: count
        for reply, count in (
            await db.execute(
                select(RadPostAuth.reply, func.count())
                .where(RadPostAuth.authdate >= since)
                .group_by(RadPostAuth.reply)
            )
        ).all()
    }

    today_start = datetime.combine(date.today(), time.min)
    download, upload = (
        await db.execute(
            select(
                func.coalesce(func.sum(RadAcct.acctoutputoctets), 0),
                func.coalesce(func.sum(RadAcct.acctinputoctets), 0),
            ).where(RadAcct.acctstarttime >= today_start)
        )
    ).one()

    return DashboardSummary(
        total_users=total_users or 0,
        online_users=online_users or 0,
        online_sessions=online_sessions or 0,
        auth_accept_24h=auth_counts.get(ACCEPT, 0),
        auth_reject_24h=auth_counts.get(REJECT, 0),
        # acctoutputoctets = sent by the NAS to the user = download.
        traffic_today_download_bytes=int(download),
        traffic_today_upload_bytes=int(upload),
    )


async def get_traffic(db: AsyncSession, *, days: int) -> list[TrafficPoint]:
    first_day = date.today() - timedelta(days=days - 1)
    day_col = func.date(RadAcct.acctstarttime)

    rows = (
        await db.execute(
            select(
                day_col,
                func.coalesce(func.sum(RadAcct.acctoutputoctets), 0),
                func.coalesce(func.sum(RadAcct.acctinputoctets), 0),
            )
            .where(RadAcct.acctstarttime >= datetime.combine(first_day, time.min))
            .group_by(day_col)
        )
    ).all()
    by_day = {row[0]: (int(row[1]), int(row[2])) for row in rows}

    points = []
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        download, upload = by_day.get(day, (0, 0))
        points.append(
            TrafficPoint(date=day.isoformat(), download_bytes=download, upload_bytes=upload)
        )
    return points


async def get_auth_stats(db: AsyncSession, *, hours: int) -> list[AuthStatPoint]:
    first_hour = (datetime.now() - timedelta(hours=hours - 1)).replace(
        minute=0, second=0, microsecond=0
    )
    day_col = func.date(RadPostAuth.authdate)
    hour_col = func.hour(RadPostAuth.authdate)

    rows = (
        await db.execute(
            select(day_col, hour_col, RadPostAuth.reply, func.count())
            .where(RadPostAuth.authdate >= first_hour)
            .group_by(day_col, hour_col, RadPostAuth.reply)
        )
    ).all()

    counts: dict[datetime, dict[str, int]] = {}
    for day, hour, reply, count in rows:
        bucket = datetime.combine(day, time(hour=int(hour)))
        counts.setdefault(bucket, {})[reply] = int(count)

    points = []
    for offset in range(hours):
        bucket = first_hour + timedelta(hours=offset)
        bucket_counts = counts.get(bucket, {})
        points.append(
            AuthStatPoint(
                hour=bucket,
                accept=bucket_counts.get(ACCEPT, 0),
                reject=bucket_counts.get(REJECT, 0),
            )
        )
    return points
