"""RADIUS user business logic.

A "user" is not a table: it is the set of radcheck rows sharing a username,
plus its radreply and radusergroup rows (CLAUDE.md section 4.1).

Transaction pattern: rely on AsyncSession autobegin and commit once at the end
of each write, so every write plus its audit row lands atomically — see
docs/decisions.md (2026-09-13, transaction pattern).
"""

from datetime import datetime

from sqlalchemy import delete, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings
from app.db.models.profile_assignment import AppProfileAssignment
from app.db.models.radius import RadAcct, RadCheck, RadReply, RadUserGroup
from app.schemas.accounting import AccountingItem
from app.schemas.common import AttributeItem
from app.schemas.user import (
    ServiceType,
    UserCreate,
    UserDetail,
    UserListItem,
    UserStatus,
    UserUpdate,
)
from app.services.audit_service import record_audit_log
from app.utils.radius_attrs import (
    DISABLED_ATTRIBUTE,
    DISABLED_VALUE,
    EXPIRATION_ATTRIBUTE,
    PASSWORD_ATTRIBUTES,
)
from app.utils.radius_expiration import (
    InvalidExpirationError,
    format_expiration,
    is_expired,
    parse_expiration,
)
from app.utils.radius_password import build_password_value
from app.utils.service_type import service_type_from_groups
from app.utils.sql import escape_like

settings = get_settings()

RESOURCE_TYPE = "radius_user"

# MariaDB STR_TO_DATE format matching EXPIRATION_FORMAT ("%d %b %Y %H:%M").
_SQL_EXPIRATION_FORMAT = "%d %b %Y %H:%i"


class UserNotFoundError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


def _disabled_exists(username_col: ColumnElement[str]) -> ColumnElement[bool]:
    rc = aliased(RadCheck)
    return (
        select(rc.id)
        .where(
            rc.username == username_col,
            rc.attribute == DISABLED_ATTRIBUTE,
            rc.value == DISABLED_VALUE,
        )
        .exists()
    )


def _expired_exists(username_col: ColumnElement[str]) -> ColumnElement[bool]:
    rc = aliased(RadCheck)
    return (
        select(rc.id)
        .where(
            rc.username == username_col,
            rc.attribute == EXPIRATION_ATTRIBUTE,
            func.str_to_date(rc.value, _SQL_EXPIRATION_FORMAT) < func.now(),
        )
        .exists()
    )


def _status_from_rows(rows: list[RadCheck]) -> UserStatus:
    """disabled wins over expired, expired over active."""
    for row in rows:
        if row.attribute == DISABLED_ATTRIBUTE and row.value == DISABLED_VALUE:
            return UserStatus.disabled
    for row in rows:
        if row.attribute == EXPIRATION_ATTRIBUTE and is_expired(row.value):
            return UserStatus.expired
    return UserStatus.active


def _expiration_from_rows(rows: list[RadCheck]) -> datetime | None:
    for row in rows:
        if row.attribute == EXPIRATION_ATTRIBUTE:
            try:
                return parse_expiration(row.value)
            except InvalidExpirationError:
                return None
    return None


def _service_type(groups: list[str]) -> ServiceType:
    """From the group naming convention only; session-based detection lives in
    the sessions API (see docs/decisions.md)."""
    return ServiceType(service_type_from_groups(groups))


async def list_users(
    db: AsyncSession,
    *,
    search: str | None = None,
    group: str | None = None,
    status: UserStatus | None = None,
    page: int = 1,
    page_size: int = 25,
    sort: str = "username",
) -> tuple[list[UserListItem], int]:
    """List users derived from radcheck, with filters and pagination."""
    username_col = RadCheck.username
    filters: list[ColumnElement[bool]] = []

    if search:
        filters.append(username_col.like(f"%{escape_like(search)}%", escape="\\"))

    if group:
        rug = aliased(RadUserGroup)
        filters.append(
            select(rug.id).where(rug.username == username_col, rug.groupname == group).exists()
        )

    if status is UserStatus.disabled:
        filters.append(_disabled_exists(username_col))
    elif status is UserStatus.expired:
        filters.append(~_disabled_exists(username_col))
        filters.append(_expired_exists(username_col))
    elif status is UserStatus.active:
        filters.append(~_disabled_exists(username_col))
        filters.append(~_expired_exists(username_col))

    base = select(distinct(username_col)).where(*filters)

    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    order = username_col.desc() if sort == "-username" else username_col.asc()
    page_stmt = base.order_by(order).limit(page_size).offset((page - 1) * page_size)
    usernames = list((await db.execute(page_stmt)).scalars().all())

    if not usernames:
        return [], total or 0

    check_rows = list(
        (await db.execute(select(RadCheck).where(RadCheck.username.in_(usernames)))).scalars().all()
    )
    group_rows = list(
        (
            await db.execute(
                select(RadUserGroup)
                .where(RadUserGroup.username.in_(usernames))
                .order_by(RadUserGroup.priority)
            )
        )
        .scalars()
        .all()
    )

    checks_by_user: dict[str, list[RadCheck]] = {name: [] for name in usernames}
    for row in check_rows:
        checks_by_user[row.username].append(row)

    groups_by_user: dict[str, list[str]] = {name: [] for name in usernames}
    for group_row in group_rows:
        groups_by_user[group_row.username].append(group_row.groupname)

    items = [
        UserListItem(
            username=name,
            status=_status_from_rows(checks_by_user[name]),
            has_password=any(
                row.attribute in PASSWORD_ATTRIBUTES for row in checks_by_user[name]
            ),
            groups=groups_by_user[name],
            service_type=_service_type(groups_by_user[name]),
            expiration=_expiration_from_rows(checks_by_user[name]),
        )
        for name in usernames
    ]
    return items, total or 0


async def get_user(db: AsyncSession, username: str) -> UserDetail:
    check_rows = list(
        (await db.execute(select(RadCheck).where(RadCheck.username == username))).scalars().all()
    )
    if not check_rows:
        raise UserNotFoundError(username)

    reply_rows = list(
        (await db.execute(select(RadReply).where(RadReply.username == username))).scalars().all()
    )
    group_rows = list(
        (
            await db.execute(
                select(RadUserGroup)
                .where(RadUserGroup.username == username)
                .order_by(RadUserGroup.priority)
            )
        )
        .scalars()
        .all()
    )
    groups = [row.groupname for row in group_rows]

    return UserDetail(
        username=username,
        status=_status_from_rows(check_rows),
        has_password=any(row.attribute in PASSWORD_ATTRIBUTES for row in check_rows),
        groups=groups,
        service_type=_service_type(groups),
        expiration=_expiration_from_rows(check_rows),
        # Password values are never exposed through the API (CLAUDE.md section 8).
        check_attributes=[
            AttributeItem(attribute=row.attribute, op=row.op, value=row.value)
            for row in check_rows
            if row.attribute not in PASSWORD_ATTRIBUTES
        ],
        reply_attributes=[
            AttributeItem(attribute=row.attribute, op=row.op, value=row.value)
            for row in reply_rows
        ],
    )


async def _username_exists(db: AsyncSession, username: str) -> bool:
    found = await db.scalar(select(RadCheck.id).where(RadCheck.username == username).limit(1))
    return found is not None


async def create_user(
    db: AsyncSession, payload: UserCreate, *, admin_id: int, ip_address: str | None
) -> UserDetail:
    if await _username_exists(db, payload.username):
        raise UserAlreadyExistsError(payload.username)

    password_attribute = settings.radius_password_attribute
    db.add(
        RadCheck(
            username=payload.username,
            attribute=password_attribute,
            op=":=",
            value=build_password_value(payload.password, password_attribute),
        )
    )

    expiration_value = format_expiration(payload.expiration) if payload.expiration else None
    if expiration_value is not None:
        db.add(
            RadCheck(
                username=payload.username,
                attribute=EXPIRATION_ATTRIBUTE,
                op=":=",
                value=expiration_value,
            )
        )

    for priority, groupname in enumerate(payload.groups, start=1):
        db.add(
            RadUserGroup(username=payload.username, groupname=groupname, priority=priority)
        )

    for item in payload.reply_attributes:
        db.add(
            RadReply(
                username=payload.username,
                attribute=item.attribute,
                op=item.op,
                value=item.value,
            )
        )

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="create",
        resource_type=RESOURCE_TYPE,
        resource_id=payload.username,
        after={
            "username": payload.username,
            "password": "***",
            "groups": payload.groups,
            "expiration": expiration_value,
            "reply_attributes": [item.model_dump() for item in payload.reply_attributes],
        },
        ip_address=ip_address,
    )
    await db.commit()

    return await get_user(db, payload.username)


async def update_user(
    db: AsyncSession,
    username: str,
    payload: UserUpdate,
    *,
    admin_id: int,
    ip_address: str | None,
) -> UserDetail:
    """Replace groups, expiration and reply attributes as one set.

    Password rows and the disabled marker are left untouched — they have their
    own endpoints.
    """
    before = await get_user(db, username)

    await db.execute(
        delete(RadCheck).where(
            RadCheck.username == username, RadCheck.attribute == EXPIRATION_ATTRIBUTE
        )
    )
    await db.execute(delete(RadReply).where(RadReply.username == username))
    await db.execute(delete(RadUserGroup).where(RadUserGroup.username == username))

    expiration_value = format_expiration(payload.expiration) if payload.expiration else None
    if expiration_value is not None:
        db.add(
            RadCheck(
                username=username,
                attribute=EXPIRATION_ATTRIBUTE,
                op=":=",
                value=expiration_value,
            )
        )

    for priority, groupname in enumerate(payload.groups, start=1):
        db.add(RadUserGroup(username=username, groupname=groupname, priority=priority))

    for item in payload.reply_attributes:
        db.add(
            RadReply(username=username, attribute=item.attribute, op=item.op, value=item.value)
        )

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="update",
        resource_type=RESOURCE_TYPE,
        resource_id=username,
        before=before.model_dump(mode="json"),
        after={
            "groups": payload.groups,
            "expiration": expiration_value,
            "reply_attributes": [item.model_dump() for item in payload.reply_attributes],
        },
        ip_address=ip_address,
    )
    await db.commit()

    return await get_user(db, username)


async def set_password(
    db: AsyncSession, username: str, password: str, *, admin_id: int, ip_address: str | None
) -> None:
    if not await _username_exists(db, username):
        raise UserNotFoundError(username)

    password_attribute = settings.radius_password_attribute
    # Drop any password row regardless of scheme, so switching
    # RADIUS_PASSWORD_ATTRIBUTE never leaves two usable passwords behind.
    await db.execute(
        delete(RadCheck).where(
            RadCheck.username == username, RadCheck.attribute.in_(PASSWORD_ATTRIBUTES)
        )
    )
    db.add(
        RadCheck(
            username=username,
            attribute=password_attribute,
            op=":=",
            value=build_password_value(password, password_attribute),
        )
    )

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="password_change",
        resource_type=RESOURCE_TYPE,
        resource_id=username,
        after={"password": "***", "attribute": password_attribute},
        ip_address=ip_address,
    )
    await db.commit()


async def set_status(
    db: AsyncSession, username: str, enabled: bool, *, admin_id: int, ip_address: str | None
) -> UserDetail:
    """Disable by adding `Auth-Type := Reject`, enable by removing it."""
    if not await _username_exists(db, username):
        raise UserNotFoundError(username)

    await db.execute(
        delete(RadCheck).where(
            RadCheck.username == username,
            RadCheck.attribute == DISABLED_ATTRIBUTE,
            RadCheck.value == DISABLED_VALUE,
        )
    )
    if not enabled:
        db.add(
            RadCheck(
                username=username,
                attribute=DISABLED_ATTRIBUTE,
                op=":=",
                value=DISABLED_VALUE,
            )
        )

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="status_change",
        resource_type=RESOURCE_TYPE,
        resource_id=username,
        after={"enabled": enabled},
        ip_address=ip_address,
    )
    await db.commit()

    return await get_user(db, username)


async def delete_user(
    db: AsyncSession, username: str, *, admin_id: int, ip_address: str | None
) -> None:
    """Delete radcheck/radreply/radusergroup rows in one transaction.

    radacct and radpostauth history is deliberately kept (CLAUDE.md 4.1).
    """
    before = await get_user(db, username)

    await db.execute(delete(RadCheck).where(RadCheck.username == username))
    await db.execute(delete(RadReply).where(RadReply.username == username))
    await db.execute(delete(RadUserGroup).where(RadUserGroup.username == username))
    await db.execute(
        delete(AppProfileAssignment).where(
            AppProfileAssignment.target_type == "user",
            AppProfileAssignment.target_name == username,
        )
    )

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="delete",
        resource_type=RESOURCE_TYPE,
        resource_id=username,
        before=before.model_dump(mode="json"),
        ip_address=ip_address,
    )
    await db.commit()


async def list_user_sessions(
    db: AsyncSession, username: str, *, page: int = 1, page_size: int = 25
) -> tuple[list[AccountingItem], int]:
    if not await _username_exists(db, username):
        raise UserNotFoundError(username)

    total = await db.scalar(
        select(func.count()).select_from(RadAcct).where(RadAcct.username == username)
    )
    rows = (
        (
            await db.execute(
                select(RadAcct)
                .where(RadAcct.username == username)
                .order_by(RadAcct.acctstarttime.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        )
        .scalars()
        .all()
    )
    return [AccountingItem.model_validate(row) for row in rows], total or 0
