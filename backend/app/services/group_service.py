"""RADIUS group business logic (radgroupcheck / radgroupreply / radusergroup).

Like users, a "group" is not a table: it is the set of rows sharing a
groupname. Same transaction pattern as user_service (autobegin + one commit).
"""

from sqlalchemy import delete, func, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.profile_assignment import AppProfileAssignment
from app.db.models.radius import RadGroupCheck, RadGroupReply, RadUserGroup
from app.schemas.common import AttributeItem
from app.schemas.group import GroupCreate, GroupDetail, GroupListItem, GroupMember, GroupUpdate
from app.services.audit_service import record_audit_log
from app.utils.sql import escape_like

RESOURCE_TYPE = "radius_group"


class GroupNotFoundError(Exception):
    pass


class GroupAlreadyExistsError(Exception):
    pass


async def list_groups(
    db: AsyncSession, *, search: str | None = None, page: int = 1, page_size: int = 25
) -> tuple[list[GroupListItem], int]:
    """Group names are the union of radgroupcheck, radgroupreply and radusergroup:
    a group can legitimately have only members, or only reply attributes."""
    check_q = select(RadGroupCheck.groupname.label("groupname"))
    reply_q = select(RadGroupReply.groupname.label("groupname"))
    member_q = select(RadUserGroup.groupname.label("groupname"))

    if search:
        pattern = f"%{escape_like(search)}%"
        check_q = check_q.where(RadGroupCheck.groupname.like(pattern, escape="\\"))
        reply_q = reply_q.where(RadGroupReply.groupname.like(pattern, escape="\\"))
        member_q = member_q.where(RadUserGroup.groupname.like(pattern, escape="\\"))

    names = union(check_q, reply_q, member_q).subquery()
    groupname_col = names.c.groupname

    total = await db.scalar(select(func.count()).select_from(names))

    groupnames = list(
        (
            await db.execute(
                select(groupname_col)
                .order_by(groupname_col.asc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        )
        .scalars()
        .all()
    )
    if not groupnames:
        return [], total or 0

    member_counts = {
        name: count
        for name, count in (
            await db.execute(
                select(RadUserGroup.groupname, func.count())
                .where(RadUserGroup.groupname.in_(groupnames))
                .group_by(RadUserGroup.groupname)
            )
        ).all()
    }

    items = [
        GroupListItem(groupname=name, member_count=member_counts.get(name, 0))
        for name in groupnames
    ]
    return items, total or 0


async def _group_exists(db: AsyncSession, groupname: str) -> bool:
    for statement in (
        select(RadGroupCheck.id).where(RadGroupCheck.groupname == groupname).limit(1),
        select(RadGroupReply.id).where(RadGroupReply.groupname == groupname).limit(1),
        select(RadUserGroup.id).where(RadUserGroup.groupname == groupname).limit(1),
    ):
        if await db.scalar(statement) is not None:
            return True
    return False


async def get_group(db: AsyncSession, groupname: str) -> GroupDetail:
    check_rows = list(
        (await db.execute(select(RadGroupCheck).where(RadGroupCheck.groupname == groupname)))
        .scalars()
        .all()
    )
    reply_rows = list(
        (await db.execute(select(RadGroupReply).where(RadGroupReply.groupname == groupname)))
        .scalars()
        .all()
    )
    member_count = await db.scalar(
        select(func.count()).select_from(RadUserGroup).where(RadUserGroup.groupname == groupname)
    )

    if not check_rows and not reply_rows and not member_count:
        raise GroupNotFoundError(groupname)

    return GroupDetail(
        groupname=groupname,
        member_count=member_count or 0,
        check_attributes=[
            AttributeItem(attribute=row.attribute, op=row.op, value=row.value)
            for row in check_rows
        ],
        reply_attributes=[
            AttributeItem(attribute=row.attribute, op=row.op, value=row.value)
            for row in reply_rows
        ],
    )


async def create_group(
    db: AsyncSession, payload: GroupCreate, *, admin_id: int, ip_address: str | None
) -> GroupDetail:
    if await _group_exists(db, payload.groupname):
        raise GroupAlreadyExistsError(payload.groupname)

    for item in payload.check_attributes:
        db.add(
            RadGroupCheck(
                groupname=payload.groupname,
                attribute=item.attribute,
                op=item.op,
                value=item.value,
            )
        )
    for item in payload.reply_attributes:
        db.add(
            RadGroupReply(
                groupname=payload.groupname,
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
        resource_id=payload.groupname,
        after=payload.model_dump(mode="json"),
        ip_address=ip_address,
    )
    await db.commit()

    return await get_group(db, payload.groupname)


async def update_group(
    db: AsyncSession,
    groupname: str,
    payload: GroupUpdate,
    *,
    admin_id: int,
    ip_address: str | None,
) -> GroupDetail:
    """Replace the group's check and reply attributes as one set."""
    before = await get_group(db, groupname)

    await db.execute(delete(RadGroupCheck).where(RadGroupCheck.groupname == groupname))
    await db.execute(delete(RadGroupReply).where(RadGroupReply.groupname == groupname))

    for item in payload.check_attributes:
        db.add(
            RadGroupCheck(
                groupname=groupname, attribute=item.attribute, op=item.op, value=item.value
            )
        )
    for item in payload.reply_attributes:
        db.add(
            RadGroupReply(
                groupname=groupname, attribute=item.attribute, op=item.op, value=item.value
            )
        )

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="update",
        resource_type=RESOURCE_TYPE,
        resource_id=groupname,
        before=before.model_dump(mode="json"),
        after=payload.model_dump(mode="json"),
        ip_address=ip_address,
    )
    await db.commit()

    return await get_group(db, groupname)


async def delete_group(
    db: AsyncSession, groupname: str, *, admin_id: int, ip_address: str | None
) -> None:
    """Delete the group's attribute rows (and its profile assignment record).

    radusergroup memberships are left alone on purpose (see docs/decisions.md):
    FreeRADIUS has no FK there, and silently unassigning users from a group is
    more destructive than leaving a membership that now grants nothing.
    """
    before = await get_group(db, groupname)

    await db.execute(delete(RadGroupCheck).where(RadGroupCheck.groupname == groupname))
    await db.execute(delete(RadGroupReply).where(RadGroupReply.groupname == groupname))
    await db.execute(
        delete(AppProfileAssignment).where(
            AppProfileAssignment.target_type == "group",
            AppProfileAssignment.target_name == groupname,
        )
    )

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="delete",
        resource_type=RESOURCE_TYPE,
        resource_id=groupname,
        before=before.model_dump(mode="json"),
        ip_address=ip_address,
    )
    await db.commit()


async def list_group_members(
    db: AsyncSession, groupname: str, *, page: int = 1, page_size: int = 25
) -> tuple[list[GroupMember], int]:
    total = await db.scalar(
        select(func.count()).select_from(RadUserGroup).where(RadUserGroup.groupname == groupname)
    )
    rows = (
        (
            await db.execute(
                select(RadUserGroup)
                .where(RadUserGroup.groupname == groupname)
                .order_by(RadUserGroup.username)
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        )
        .scalars()
        .all()
    )
    return [GroupMember(username=row.username, priority=row.priority) for row in rows], total or 0
