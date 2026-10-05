"""Online sessions, Disconnect (PoD) and CoA (CLAUDE.md sections 1 and 6.1)."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings
from app.db.models.bandwidth_profile import AppBandwidthProfile
from app.db.models.radius import RadAcct
from app.schemas.sessions import OnlineSessionItem, SessionCapabilities
from app.services.audit_service import record_audit_log
from app.services.mikrotik_shaping import (
    RATE_LIMIT_ATTRIBUTE,
    RateLimitParseError,
    build_rate_limit,
    parse_rate_limit,
    profile_from_fields,
    validate_rate_limit,
)
from app.services.nas_service import find_secret_for_nas_ip
from app.services.radclient import DynAuthCommand, DynAuthResult, send_dynauth
from app.services.session_classifier import classify_session, service_filter
from app.services.shaping_service import PROFILE_FIELD_NAMES, ProfileNotFoundError

RESOURCE_TYPE = "session"


class SessionNotFoundError(Exception):
    pass


class SessionNotOnlineError(Exception):
    pass


class NasSecretNotFoundError(Exception):
    pass


class InvalidCoaRequestError(Exception):
    pass


def get_capabilities() -> SessionCapabilities:
    settings = get_settings()
    return SessionCapabilities(pod_enabled=settings.enable_pod, coa_enabled=settings.enable_coa)


def _to_online_item(row: RadAcct) -> OnlineSessionItem:
    data = {
        name: getattr(row, name) for name in OnlineSessionItem.model_fields if name != "service_type"
    }
    return OnlineSessionItem(
        **data,
        service_type=classify_session(
            nasporttype=row.nasporttype,
            servicetype=row.servicetype,
            framedprotocol=row.framedprotocol,
        ),
    )


async def list_online_sessions(
    db: AsyncSession, *, service: str = "all", page: int = 1, page_size: int = 25
) -> tuple[list[OnlineSessionItem], int]:
    conditions: list[ColumnElement[bool]] = [RadAcct.acctstoptime.is_(None)]
    service_condition = service_filter(service)
    if service_condition is not None:
        conditions.append(service_condition)
    excluded_usernames = get_settings().online_sessions_exclude_usernames_list
    if excluded_usernames:
        # username is nullable; NULL NOT IN (...) is NULL (falsy) in SQL, which
        # would silently drop those rows too, so keep them explicitly.
        conditions.append(
            or_(RadAcct.username.is_(None), RadAcct.username.notin_(excluded_usernames))
        )

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
    return [_to_online_item(row) for row in rows], total or 0


async def _load_online_session(db: AsyncSession, radacctid: int) -> RadAcct:
    session = await db.get(RadAcct, radacctid)
    if session is None:
        raise SessionNotFoundError(radacctid)
    if session.acctstoptime is not None:
        raise SessionNotOnlineError(radacctid)
    return session


def _identity_attributes(session: RadAcct) -> list[tuple[str, str]]:
    attributes = [
        ("User-Name", session.username or ""),
        ("Acct-Session-Id", session.acctsessionid),
        ("NAS-IP-Address", session.nasipaddress),
    ]
    if session.framedipaddress:
        attributes.append(("Framed-IP-Address", session.framedipaddress))
    return attributes


async def _send(
    db: AsyncSession,
    session: RadAcct,
    command: DynAuthCommand,
    extra_attributes: list[tuple[str, str]],
) -> DynAuthResult:
    secret = await find_secret_for_nas_ip(db, session.nasipaddress)
    if secret is None:
        raise NasSecretNotFoundError(session.nasipaddress)

    settings = get_settings()
    try:
        return await send_dynauth(
            radclient_path=settings.radclient_path,
            nas_ip=session.nasipaddress,
            port=settings.radius_dynauth_port,
            secret=secret,
            command=command,
            attributes=_identity_attributes(session) + extra_attributes,
            timeout_sec=settings.radclient_timeout_sec,
        )
    except ValueError as exc:
        # Invalid NAS address or an attribute value with line breaks.
        return DynAuthResult(success=False, response=None, error_cause=None, detail=str(exc))


async def _audit_result(
    db: AsyncSession,
    session: RadAcct,
    action: str,
    result: DynAuthResult,
    extra: dict[str, object],
    *,
    admin_id: int,
    ip_address: str | None,
) -> None:
    await record_audit_log(
        db,
        admin_id=admin_id,
        action=action,
        resource_type=RESOURCE_TYPE,
        resource_id=str(session.radacctid),
        after={
            "username": session.username,
            "nasipaddress": session.nasipaddress,
            "acctsessionid": session.acctsessionid,
            **extra,
            "result": {
                "success": result.success,
                "response": result.response,
                "error_cause": result.error_cause,
                "detail": result.detail,
            },
        },
        ip_address=ip_address,
    )
    await db.commit()


async def disconnect_session(
    db: AsyncSession, radacctid: int, *, admin_id: int, ip_address: str | None
) -> DynAuthResult:
    session = await _load_online_session(db, radacctid)
    result = await _send(db, session, "disconnect", [])
    await _audit_result(
        db, session, "disconnect", result, {}, admin_id=admin_id, ip_address=ip_address
    )
    return result


async def change_session_speed(
    db: AsyncSession,
    radacctid: int,
    *,
    profile_id: int | None,
    rate_limit: str | None,
    admin_id: int,
    ip_address: str | None,
) -> DynAuthResult:
    session = await _load_online_session(db, radacctid)

    extra_attributes: list[tuple[str, str]] = []
    audit_extra: dict[str, object] = {}

    if profile_id is not None:
        profile_row = await db.get(AppBandwidthProfile, profile_id)
        if profile_row is None:
            raise ProfileNotFoundError(profile_id)
        profile = profile_from_fields(
            {name: getattr(profile_row, name) for name in PROFILE_FIELD_NAMES}
        )
        if profile.rate_limit is None:
            raise InvalidCoaRequestError("profile has no Mikrotik-Rate-Limit to send")
        rate_limit_string = build_rate_limit(profile.rate_limit)
        extra_attributes.append((RATE_LIMIT_ATTRIBUTE, rate_limit_string))
        if profile.session_timeout_sec is not None:
            extra_attributes.append(("Session-Timeout", str(profile.session_timeout_sec)))
        audit_extra = {"profile_id": profile_id, "rate_limit": rate_limit_string}
    else:
        assert rate_limit is not None
        try:
            parsed = parse_rate_limit(rate_limit)
        except RateLimitParseError as exc:
            raise InvalidCoaRequestError(str(exc)) from exc
        errors = validate_rate_limit(parsed)
        if errors:
            raise InvalidCoaRequestError("; ".join(errors))
        rate_limit_string = build_rate_limit(parsed)
        extra_attributes.append((RATE_LIMIT_ATTRIBUTE, rate_limit_string))
        audit_extra = {"rate_limit": rate_limit_string}

    result = await _send(db, session, "coa", extra_attributes)
    await _audit_result(
        db, session, "coa", result, audit_extra, admin_id=admin_id, ip_address=ip_address
    )
    return result
