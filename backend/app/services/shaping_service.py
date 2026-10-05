"""Bandwidth profile CRUD and applying profiles to groups/users (CLAUDE.md 6.1).

All attribute/string building is delegated to mikrotik_shaping.
Transaction pattern: autobegin + one commit per write (docs/decisions.md).
"""

from dataclasses import asdict
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.bandwidth_profile import AppBandwidthProfile
from app.db.models.profile_assignment import AppProfileAssignment
from app.db.models.radius import RadCheck, RadGroupCheck, RadGroupReply, RadReply, RadUserGroup
from app.schemas.common import AttributeItem
from app.schemas.shaping import (
    ApplyResponse,
    AssignedProfile,
    EffectiveAttribute,
    EffectiveShapingResponse,
    ParseResponse,
    PreviewResponse,
    ProfileFieldsData,
    ProfileOut,
    ProfileWrite,
    ShapingFields,
    TargetOut,
)
from app.services.audit_service import record_audit_log
from app.services.mikrotik_shaping import (
    RATE_LIMIT_ATTRIBUTE,
    SHAPING_REPLY_ATTRIBUTES,
    SIMULTANEOUS_USE_ATTRIBUTE,
    Attribute,
    build_attributes,
    parse_rate_limit,
    profile_from_fields,
)
from app.utils.service_type import HOTSPOT, PPPOE, service_type_from_groups
from app.utils.sql import escape_like

RESOURCE_TYPE = "shaping_profile"

# FreeRADIUS reads radreply BEFORE radgroupreply, and a group reply written
# with `:=` would REPLACE the user's value. Group replies are therefore written
# with `=` ("add only if not already present"), which is what lets a per-user
# override actually win (CLAUDE.md 6.1). User-level applies keep `:=`.
# See docs/decisions.md.
GROUP_REPLY_OPERATOR = "="

PROFILE_FIELD_NAMES: tuple[str, ...] = tuple(ProfileFieldsData.model_fields)

TargetType = Literal["group", "user"]


class ProfileNotFoundError(Exception):
    pass


class ProfileNameExistsError(Exception):
    pass


class ProfileInUseError(Exception):
    pass


class ShapingTargetNotFoundError(Exception):
    def __init__(self, target: str, name: str) -> None:
        super().__init__(f"{target} '{name}' not found")
        self.target = target
        self.name = name


class ProfileServiceMismatchError(Exception):
    def __init__(self, profile_service: str, target_service: str) -> None:
        super().__init__(
            f"Profile is for {profile_service} but the target is {target_service}"
        )
        self.profile_service = profile_service
        self.target_service = target_service


def _values(row: AppBandwidthProfile) -> dict[str, Any]:
    return {name: getattr(row, name) for name in PROFILE_FIELD_NAMES}


def _to_items(attributes: list[Attribute]) -> list[AttributeItem]:
    return [AttributeItem(attribute=name, op=op, value=value) for name, op, value in attributes]


def _to_out(row: AppBandwidthProfile, target_count: int) -> ProfileOut:
    values = _values(row)
    attributes = build_attributes(profile_from_fields(values))
    return ProfileOut(
        id=row.id,
        name=row.name,
        description=row.description,
        is_active=row.is_active,
        rate_limit_string=attributes.rate_limit_string,
        target_count=target_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
        **values,
    )


async def _target_counts(db: AsyncSession, profile_ids: list[int]) -> dict[int, int]:
    if not profile_ids:
        return {}
    rows = await db.execute(
        select(AppProfileAssignment.profile_id, func.count())
        .where(AppProfileAssignment.profile_id.in_(profile_ids))
        .group_by(AppProfileAssignment.profile_id)
    )
    return {profile_id: count for profile_id, count in rows.all()}


async def _get_row(db: AsyncSession, profile_id: int) -> AppBandwidthProfile:
    row = await db.get(AppBandwidthProfile, profile_id)
    if row is None:
        raise ProfileNotFoundError(profile_id)
    return row


async def _name_taken(db: AsyncSession, name: str, *, exclude_id: int | None = None) -> bool:
    statement = select(AppBandwidthProfile.id).where(AppBandwidthProfile.name == name)
    if exclude_id is not None:
        statement = statement.where(AppBandwidthProfile.id != exclude_id)
    return await db.scalar(statement.limit(1)) is not None


async def list_profiles(
    db: AsyncSession, *, search: str | None = None, page: int = 1, page_size: int = 25
) -> tuple[list[ProfileOut], int]:
    conditions = []
    if search:
        conditions.append(
            AppBandwidthProfile.name.like(f"%{escape_like(search)}%", escape="\\")
        )

    total = await db.scalar(
        select(func.count()).select_from(AppBandwidthProfile).where(*conditions)
    )
    rows = list(
        (
            await db.execute(
                select(AppBandwidthProfile)
                .where(*conditions)
                .order_by(AppBandwidthProfile.name)
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        )
        .scalars()
        .all()
    )
    counts = await _target_counts(db, [row.id for row in rows])
    return [_to_out(row, counts.get(row.id, 0)) for row in rows], total or 0


async def get_profile(db: AsyncSession, profile_id: int) -> ProfileOut:
    row = await _get_row(db, profile_id)
    counts = await _target_counts(db, [row.id])
    return _to_out(row, counts.get(row.id, 0))


async def create_profile(
    db: AsyncSession, payload: ProfileWrite, *, admin_id: int, ip_address: str | None
) -> ProfileOut:
    if await _name_taken(db, payload.name):
        raise ProfileNameExistsError(payload.name)

    row = AppBandwidthProfile(**payload.model_dump())
    db.add(row)
    await db.flush()

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="create",
        resource_type=RESOURCE_TYPE,
        resource_id=str(row.id),
        after=payload.model_dump(mode="json"),
        ip_address=ip_address,
    )
    await db.commit()
    return _to_out(row, 0)


async def update_profile(
    db: AsyncSession,
    profile_id: int,
    payload: ProfileWrite,
    *,
    admin_id: int,
    ip_address: str | None,
) -> ProfileOut:
    """Update the profile only. Re-applying to existing targets is a separate,
    explicit action (CLAUDE.md 6.1: ask, never automatic)."""
    row = await _get_row(db, profile_id)
    if await _name_taken(db, payload.name, exclude_id=profile_id):
        raise ProfileNameExistsError(payload.name)

    counts = await _target_counts(db, [row.id])
    before = _to_out(row, counts.get(row.id, 0)).model_dump(mode="json")

    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="update",
        resource_type=RESOURCE_TYPE,
        resource_id=str(row.id),
        before=before,
        after=payload.model_dump(mode="json"),
        ip_address=ip_address,
    )
    await db.commit()
    return _to_out(row, counts.get(row.id, 0))


async def delete_profile(
    db: AsyncSession, profile_id: int, *, admin_id: int, ip_address: str | None
) -> None:
    """Refuses while the profile is still assigned anywhere (see docs/decisions.md)."""
    row = await _get_row(db, profile_id)
    counts = await _target_counts(db, [row.id])
    if counts.get(row.id, 0) > 0:
        raise ProfileInUseError(profile_id)

    before = _to_out(row, 0).model_dump(mode="json")
    await db.delete(row)
    await record_audit_log(
        db,
        admin_id=admin_id,
        action="delete",
        resource_type=RESOURCE_TYPE,
        resource_id=str(profile_id),
        before=before,
        ip_address=ip_address,
    )
    await db.commit()


def preview(fields: ShapingFields) -> PreviewResponse:
    attributes = build_attributes(profile_from_fields(fields.model_dump()))
    return PreviewResponse(
        attributes=_to_items(attributes.reply),
        check_attributes=_to_items(attributes.check),
        rate_limit_string=attributes.rate_limit_string,
    )


def parse(rate_limit: str) -> ParseResponse:
    """Raises mikrotik_shaping.RateLimitParseError for malformed strings."""
    return ParseResponse(**asdict(parse_rate_limit(rate_limit)))


async def _user_groups(db: AsyncSession, username: str) -> list[str]:
    rows = await db.execute(
        select(RadUserGroup.groupname)
        .where(RadUserGroup.username == username)
        .order_by(RadUserGroup.priority)
    )
    return list(rows.scalars().all())


async def _apply_without_commit(
    db: AsyncSession,
    row: AppBandwidthProfile,
    target: TargetType,
    name: str,
    *,
    admin_id: int,
) -> ApplyResponse:
    profile = profile_from_fields(_values(row))
    attributes = build_attributes(profile)

    if target == "user":
        exists = await db.scalar(select(RadCheck.id).where(RadCheck.username == name).limit(1))
        if exists is None:
            raise ShapingTargetNotFoundError(target, name)
        target_service = service_type_from_groups(await _user_groups(db, name))
    else:
        target_service = service_type_from_groups([name])

    if (
        profile.service_type in (PPPOE, HOTSPOT)
        and target_service in (PPPOE, HOTSPOT)
        and profile.service_type != target_service
    ):
        raise ProfileServiceMismatchError(profile.service_type, target_service)

    # Remove the previous shaping set first so nothing is duplicated.
    if target == "user":
        await db.execute(
            delete(RadReply).where(
                RadReply.username == name, RadReply.attribute.in_(SHAPING_REPLY_ATTRIBUTES)
            )
        )
        if attributes.check:
            await db.execute(
                delete(RadCheck).where(
                    RadCheck.username == name, RadCheck.attribute == SIMULTANEOUS_USE_ATTRIBUTE
                )
            )
        for attribute, op, value in attributes.reply:
            db.add(RadReply(username=name, attribute=attribute, op=op, value=value))
        for attribute, op, value in attributes.check:
            db.add(RadCheck(username=name, attribute=attribute, op=op, value=value))
        reply_items = _to_items(attributes.reply)
    else:
        await db.execute(
            delete(RadGroupReply).where(
                RadGroupReply.groupname == name,
                RadGroupReply.attribute.in_(SHAPING_REPLY_ATTRIBUTES),
            )
        )
        if attributes.check:
            await db.execute(
                delete(RadGroupCheck).where(
                    RadGroupCheck.groupname == name,
                    RadGroupCheck.attribute == SIMULTANEOUS_USE_ATTRIBUTE,
                )
            )
        for attribute, _, value in attributes.reply:
            db.add(
                RadGroupReply(
                    groupname=name, attribute=attribute, op=GROUP_REPLY_OPERATOR, value=value
                )
            )
        for attribute, op, value in attributes.check:
            db.add(RadGroupCheck(groupname=name, attribute=attribute, op=op, value=value))
        reply_items = [
            AttributeItem(attribute=attribute, op=GROUP_REPLY_OPERATOR, value=value)
            for attribute, _, value in attributes.reply
        ]

    await db.execute(
        delete(AppProfileAssignment).where(
            AppProfileAssignment.target_type == target,
            AppProfileAssignment.target_name == name,
        )
    )
    db.add(
        AppProfileAssignment(
            profile_id=row.id,
            target_type=target,
            target_name=name,
            applied_at=datetime.utcnow(),
            applied_by=admin_id,
        )
    )

    return ApplyResponse(
        target=target,
        name=name,
        attributes=reply_items,
        check_attributes=_to_items(attributes.check),
    )


async def apply_profile(
    db: AsyncSession,
    profile_id: int,
    target: TargetType,
    name: str,
    *,
    admin_id: int,
    ip_address: str | None,
) -> ApplyResponse:
    row = await _get_row(db, profile_id)
    result = await _apply_without_commit(db, row, target, name, admin_id=admin_id)

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="apply",
        resource_type=RESOURCE_TYPE,
        resource_id=str(row.id),
        after={"profile": row.name, **result.model_dump(mode="json")},
        ip_address=ip_address,
    )
    await db.commit()
    return result


async def list_targets(db: AsyncSession, profile_id: int) -> list[TargetOut]:
    await _get_row(db, profile_id)
    rows = (
        (
            await db.execute(
                select(AppProfileAssignment)
                .where(AppProfileAssignment.profile_id == profile_id)
                .order_by(AppProfileAssignment.target_type, AppProfileAssignment.target_name)
            )
        )
        .scalars()
        .all()
    )
    return [
        TargetOut(
            target_type=row.target_type, target_name=row.target_name, applied_at=row.applied_at
        )
        for row in rows
    ]


async def reapply_profile(
    db: AsyncSession, profile_id: int, *, admin_id: int, ip_address: str | None
) -> list[TargetOut]:
    """Re-apply to every recorded target in one transaction (all or nothing)."""
    row = await _get_row(db, profile_id)
    targets = [
        (target_type, target_name)
        for target_type, target_name in (
            await db.execute(
                select(AppProfileAssignment.target_type, AppProfileAssignment.target_name)
                .where(AppProfileAssignment.profile_id == profile_id)
                .order_by(AppProfileAssignment.target_type, AppProfileAssignment.target_name)
            )
        ).all()
    ]

    for target_type, target_name in targets:
        target: TargetType = "user" if target_type == "user" else "group"
        await _apply_without_commit(db, row, target, target_name, admin_id=admin_id)

    await record_audit_log(
        db,
        admin_id=admin_id,
        action="reapply",
        resource_type=RESOURCE_TYPE,
        resource_id=str(row.id),
        after={
            "profile": row.name,
            "targets": [{"target": t, "name": n} for t, n in targets],
        },
        ip_address=ip_address,
    )
    await db.commit()
    return await list_targets(db, profile_id)


def _merge_reply(
    effective: dict[str, EffectiveAttribute], items: list[AttributeItem], source: str
) -> None:
    """Model FreeRADIUS reply merging: `:=` replaces, `=`/`+=` only add if absent."""
    for item in items:
        if item.op == ":=" or (item.op in ("=", "+=") and item.attribute not in effective):
            effective[item.attribute] = EffectiveAttribute(
                attribute=item.attribute, op=item.op, value=item.value, source=source
            )


async def get_effective_shaping(db: AsyncSession, username: str) -> EffectiveShapingResponse:
    """What shaping a user actually gets: own radreply first, then groups by
    priority — and where each value comes from (CLAUDE.md 6.1)."""
    exists = await db.scalar(select(RadCheck.id).where(RadCheck.username == username).limit(1))
    if exists is None:
        raise ShapingTargetNotFoundError("user", username)

    user_rows = (
        (
            await db.execute(
                select(RadReply)
                .where(
                    RadReply.username == username,
                    RadReply.attribute.in_(SHAPING_REPLY_ATTRIBUTES),
                )
                .order_by(RadReply.id)
            )
        )
        .scalars()
        .all()
    )
    user_attributes = [
        AttributeItem(attribute=row.attribute, op=row.op, value=row.value) for row in user_rows
    ]

    groups = await _user_groups(db, username)
    group_attributes: dict[str, list[AttributeItem]] = {group: [] for group in groups}
    if groups:
        group_rows = (
            (
                await db.execute(
                    select(RadGroupReply)
                    .where(
                        RadGroupReply.groupname.in_(groups),
                        RadGroupReply.attribute.in_(SHAPING_REPLY_ATTRIBUTES),
                    )
                    .order_by(RadGroupReply.id)
                )
            )
            .scalars()
            .all()
        )
        for row in group_rows:
            group_attributes[row.groupname].append(
                AttributeItem(attribute=row.attribute, op=row.op, value=row.value)
            )

    effective: dict[str, EffectiveAttribute] = {}
    _merge_reply(effective, user_attributes, "user")
    for group in groups:
        _merge_reply(effective, group_attributes[group], f"group:{group}")

    assignment_rows = (
        await db.execute(
            select(
                AppProfileAssignment.target_type,
                AppProfileAssignment.target_name,
                AppBandwidthProfile.id,
                AppBandwidthProfile.name,
            )
            .join(AppBandwidthProfile, AppBandwidthProfile.id == AppProfileAssignment.profile_id)
            .where(
                or_(
                    and_(
                        AppProfileAssignment.target_type == "user",
                        AppProfileAssignment.target_name == username,
                    ),
                    and_(
                        AppProfileAssignment.target_type == "group",
                        AppProfileAssignment.target_name.in_(groups),
                    ),
                )
            )
        )
    ).all()
    profiles = [
        AssignedProfile(
            profile_id=profile_id,
            profile_name=profile_name,
            target_type=target_type,
            target_name=target_name,
        )
        for target_type, target_name, profile_id, profile_name in assignment_rows
    ]

    # CLAUDE.md 6.1: warn when more than one group shapes the same service.
    shaping_groups_per_service: dict[str, int] = {}
    for group in groups:
        if any(item.attribute == RATE_LIMIT_ATTRIBUTE for item in group_attributes[group]):
            service = service_type_from_groups([group])
            shaping_groups_per_service[service] = shaping_groups_per_service.get(service, 0) + 1
    warnings = [
        f"multiple_shaping_groups:{service}"
        for service, count in sorted(shaping_groups_per_service.items())
        if count > 1
    ]

    return EffectiveShapingResponse(
        username=username,
        groups=groups,
        profiles=profiles,
        user_attributes=user_attributes,
        group_attributes=group_attributes,
        effective=sorted(effective.values(), key=lambda item: item.attribute),
        warnings=warnings,
    )
