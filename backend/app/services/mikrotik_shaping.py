"""MikroTik traffic shaping — the ONLY place Mikrotik-Rate-Limit strings and the
related VSAs are built, parsed or validated (CLAUDE.md section 6.1). The
frontend calls POST /shaping/preview instead of re-implementing any of this.

Direction gotcha (the most common bug): in Mikrotik-Rate-Limit "rx" is what the
router receives from the client, i.e. the user's UPLOAD, and "tx" is the user's
DOWNLOAD. Every field here is named download/upload, and strings are always
written upload/download.

Format:
  rx-rate[/tx-rate] [rx-burst-rate[/tx-burst-rate] [rx-burst-threshold[/tx-burst-threshold]
  [rx-burst-time[/tx-burst-time] [priority] [rx-rate-min[/tx-rate-min]]]]]

This module also builds the one UniFi-relevant attribute a profile can carry:
UniFi Network Controller has no RADIUS VSA for rate limits, it looks the limits
up locally from a Filter-Id matching a Bandwidth Profile pre-created in the
controller (Settings > Profiles > Bandwidth Profiles) — see
docs/decisions.md "UniFi traffic shaping via Filter-Id".
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

DEFAULT_PRIORITY = 8
ACCT_INTERIM_INTERVAL_SEC = 300
MAX_QUOTA_BYTES = 2**64 - 1
ADDRESS_LIST_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SERVICE_TYPES = ("pppoe", "hotspot", "both")

RATE_LIMIT_ATTRIBUTE = "Mikrotik-Rate-Limit"
SIMULTANEOUS_USE_ATTRIBUTE = "Simultaneous-Use"
FILTER_ID_ATTRIBUTE = "Filter-Id"
UNIFI_FILTER_ID_PATTERN = re.compile(r"^[^\x00-\x1f\x7f]{1,64}$")

# Every reply attribute build_attributes() can write. Applying a profile removes
# all of them from the target first, so re-applying never leaves duplicates.
SHAPING_REPLY_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "Mikrotik-Rate-Limit",
        "Mikrotik-Address-List",
        "Mikrotik-Total-Limit",
        "Mikrotik-Total-Limit-Gigawords",
        "Mikrotik-Recv-Limit",
        "Mikrotik-Recv-Limit-Gigawords",
        "Mikrotik-Xmit-Limit",
        "Mikrotik-Xmit-Limit-Gigawords",
        "Mikrotik-Group",
        "Framed-Pool",
        "Session-Timeout",
        "Idle-Timeout",
        "Acct-Interim-Interval",
        "WISPr-Bandwidth-Max-Down",
        "WISPr-Bandwidth-Max-Up",
        "Filter-Id",
    }
)

_BURST_FIELDS = (
    "burst_download_kbps",
    "burst_upload_kbps",
    "burst_threshold_download_kbps",
    "burst_threshold_upload_kbps",
    "burst_time_sec",
)
_MIN_FIELDS = ("min_download_kbps", "min_upload_kbps")

_RATE_TOKEN = re.compile(r"^(\d+(?:\.\d+)?)([kKmMgG]?)$")
_UNIT_TO_KBPS = {"": 0.001, "k": 1.0, "m": 1_000.0, "g": 1_000_000.0}
_TIME_TOKEN = re.compile(r"^(\d+)s?$")
_PRIORITY_TOKEN = re.compile(r"^(\d+)$")

Attribute = tuple[str, str, str]


class RateLimitParseError(ValueError):
    pass


@dataclass(frozen=True)
class RateLimit:
    download_kbps: int
    upload_kbps: int
    burst_download_kbps: int | None = None
    burst_upload_kbps: int | None = None
    burst_threshold_download_kbps: int | None = None
    burst_threshold_upload_kbps: int | None = None
    burst_time_sec: int | None = None
    priority: int = DEFAULT_PRIORITY
    min_download_kbps: int | None = None
    min_upload_kbps: int | None = None

    @property
    def has_burst(self) -> bool:
        return all(getattr(self, name) is not None for name in _BURST_FIELDS)

    @property
    def has_min(self) -> bool:
        return all(getattr(self, name) is not None for name in _MIN_FIELDS)


@dataclass(frozen=True)
class ShapingProfile:
    service_type: str
    rate_limit: RateLimit | None
    session_timeout_sec: int | None = None
    idle_timeout_sec: int | None = None
    simultaneous_use: int | None = None
    mikrotik_group: str | None = None
    framed_pool: str | None = None
    total_quota_bytes: int | None = None
    address_list: str | None = None
    unifi_filter_id: str | None = None


@dataclass(frozen=True)
class ShapingAttributes:
    reply: list[Attribute]
    check: list[Attribute]
    rate_limit_string: str | None


# --------------------------------------------------------------------------- build


def _format_rate(kbps: int) -> str:
    """kbps -> "20M" when divisible by 1000, otherwise "1500k"."""
    if kbps % 1000 == 0:
        return f"{kbps // 1000}M"
    return f"{kbps}k"


def _pair(upload_kbps: int, download_kbps: int) -> str:
    return f"{_format_rate(upload_kbps)}/{_format_rate(download_kbps)}"


def build_rate_limit(rate: RateLimit) -> str:
    """Build a Mikrotik-Rate-Limit string (upload/download order)."""
    main = _pair(rate.upload_kbps, rate.download_kbps)
    parts = [main]

    has_min = rate.has_min
    has_priority = rate.priority != DEFAULT_PRIORITY or has_min
    has_burst = rate.has_burst

    # A later segment requires every earlier one to be present.
    if has_burst:
        assert rate.burst_upload_kbps is not None and rate.burst_download_kbps is not None
        assert rate.burst_threshold_upload_kbps is not None
        assert rate.burst_threshold_download_kbps is not None
        parts.append(_pair(rate.burst_upload_kbps, rate.burst_download_kbps))
        parts.append(_pair(rate.burst_threshold_upload_kbps, rate.burst_threshold_download_kbps))
        parts.append(f"{rate.burst_time_sec}/{rate.burst_time_sec}")
    elif has_priority:
        # No burst but a priority is needed: burst == rate with 0s effectively
        # disables bursting (CLAUDE.md 6.1 — "use the main rate instead").
        parts.extend([main, main, "0/0"])

    if has_priority:
        parts.append(str(rate.priority))

    if has_min:
        assert rate.min_upload_kbps is not None and rate.min_download_kbps is not None
        parts.append(_pair(rate.min_upload_kbps, rate.min_download_kbps))

    return " ".join(parts)


def split_quota(total_bytes: int) -> tuple[int, int]:
    """Split a 64-bit byte count into (low 32 bits, high 32 bits / Gigawords)."""
    return total_bytes & 0xFFFFFFFF, total_bytes >> 32


def build_attributes(profile: ShapingProfile) -> ShapingAttributes:
    """All RADIUS attributes a profile produces, with `:=` operators."""
    reply: list[Attribute] = []
    rate_limit_string: str | None = None

    if profile.rate_limit is not None:
        rate_limit_string = build_rate_limit(profile.rate_limit)
        reply.append((RATE_LIMIT_ATTRIBUTE, ":=", rate_limit_string))
        if profile.service_type == "hotspot":
            # WISPr values are bps; MikroTik gives Rate-Limit precedence anyway.
            reply.append(
                ("WISPr-Bandwidth-Max-Down", ":=", str(profile.rate_limit.download_kbps * 1000))
            )
            reply.append(
                ("WISPr-Bandwidth-Max-Up", ":=", str(profile.rate_limit.upload_kbps * 1000))
            )

    if profile.address_list:
        reply.append(("Mikrotik-Address-List", ":=", profile.address_list))

    if profile.unifi_filter_id:
        # Not a rate string: UniFi looks this up locally against a Bandwidth
        # Profile of the same name (see module docstring).
        reply.append((FILTER_ID_ATTRIBUTE, ":=", profile.unifi_filter_id))

    if profile.total_quota_bytes is not None:
        low, high = split_quota(profile.total_quota_bytes)
        reply.append(("Mikrotik-Total-Limit", ":=", str(low)))
        reply.append(("Mikrotik-Total-Limit-Gigawords", ":=", str(high)))

    if profile.mikrotik_group:
        reply.append(("Mikrotik-Group", ":=", profile.mikrotik_group))

    if profile.framed_pool and profile.service_type != "hotspot":
        reply.append(("Framed-Pool", ":=", profile.framed_pool))

    if profile.session_timeout_sec is not None:
        reply.append(("Session-Timeout", ":=", str(profile.session_timeout_sec)))

    if profile.idle_timeout_sec is not None:
        reply.append(("Idle-Timeout", ":=", str(profile.idle_timeout_sec)))

    reply.append(("Acct-Interim-Interval", ":=", str(ACCT_INTERIM_INTERVAL_SEC)))

    check: list[Attribute] = []
    if profile.simultaneous_use is not None:
        check.append((SIMULTANEOUS_USE_ATTRIBUTE, ":=", str(profile.simultaneous_use)))

    return ShapingAttributes(reply=reply, check=check, rate_limit_string=rate_limit_string)


# --------------------------------------------------------------------------- parse


def _parse_rate(token: str) -> int:
    match = _RATE_TOKEN.match(token)
    if match is None:
        raise RateLimitParseError(f"Invalid rate: {token!r}")
    return round(float(match.group(1)) * _UNIT_TO_KBPS[match.group(2).lower()])


def _split_pair(token: str) -> tuple[str, str]:
    """"rx/tx" -> (rx, tx); a single value applies to both directions."""
    pieces = token.split("/")
    if len(pieces) == 1:
        return pieces[0], pieces[0]
    if len(pieces) == 2:
        return pieces[0], pieces[1]
    raise RateLimitParseError(f"Invalid pair: {token!r}")


def _parse_rate_pair(token: str) -> tuple[int, int]:
    """Returns (upload_kbps, download_kbps) — rx first."""
    rx, tx = _split_pair(token)
    return _parse_rate(rx), _parse_rate(tx)


def _parse_time(token: str) -> int:
    # Only one burst_time field is stored; the rx (upload) value is used.
    rx, _ = _split_pair(token)
    match = _TIME_TOKEN.match(rx)
    if match is None:
        raise RateLimitParseError(f"Invalid burst time: {token!r}")
    return int(match.group(1))


def _parse_priority(token: str) -> int:
    rx, _ = _split_pair(token)
    match = _PRIORITY_TOKEN.match(rx)
    if match is None:
        raise RateLimitParseError(f"Invalid priority: {token!r}")
    return int(match.group(1))


def parse_rate_limit(value: str) -> RateLimit:
    """Parse any Mikrotik-Rate-Limit string found in the DB (k/M/G/bps, with or
    without burst). parse_rate_limit(build_rate_limit(x)) == x for valid x."""
    tokens = value.split()
    if not 1 <= len(tokens) <= 6:
        raise RateLimitParseError(f"Expected 1-6 segments, got {len(tokens)}")

    upload, download = _parse_rate_pair(tokens[0])
    fields: dict[str, Any] = {"download_kbps": download, "upload_kbps": upload}

    if len(tokens) >= 2:
        fields["burst_upload_kbps"], fields["burst_download_kbps"] = _parse_rate_pair(tokens[1])
    if len(tokens) >= 3:
        (
            fields["burst_threshold_upload_kbps"],
            fields["burst_threshold_download_kbps"],
        ) = _parse_rate_pair(tokens[2])
    if len(tokens) >= 4:
        fields["burst_time_sec"] = _parse_time(tokens[3])
    if len(tokens) >= 5:
        fields["priority"] = _parse_priority(tokens[4])
    if len(tokens) >= 6:
        fields["min_upload_kbps"], fields["min_download_kbps"] = _parse_rate_pair(tokens[5])

    rate = RateLimit(**fields)

    # Undo the "burst disabled" filler build_rate_limit() writes when only a
    # priority/min-rate is set, so round-trips hold.
    if (
        rate.burst_download_kbps == rate.download_kbps
        and rate.burst_upload_kbps == rate.upload_kbps
        and rate.burst_threshold_download_kbps == rate.download_kbps
        and rate.burst_threshold_upload_kbps == rate.upload_kbps
        and rate.burst_time_sec == 0
    ):
        rate = replace(
            rate,
            burst_download_kbps=None,
            burst_upload_kbps=None,
            burst_threshold_download_kbps=None,
            burst_threshold_upload_kbps=None,
            burst_time_sec=None,
        )
    return rate


# ------------------------------------------------------------------------ validate


def validate_rate_limit(rate: RateLimit) -> list[str]:
    errors: list[str] = []
    if rate.download_kbps <= 0 or rate.upload_kbps <= 0:
        errors.append("download and upload rate must be greater than 0")

    burst_values = [getattr(rate, name) for name in _BURST_FIELDS]
    if any(value is not None for value in burst_values):
        if any(value is None for value in burst_values):
            errors.append(
                "burst needs burst rate, burst threshold (both directions) and burst time"
            )
        else:
            assert rate.burst_download_kbps is not None and rate.burst_upload_kbps is not None
            assert rate.burst_threshold_download_kbps is not None
            assert rate.burst_threshold_upload_kbps is not None
            assert rate.burst_time_sec is not None
            if (
                rate.burst_download_kbps < rate.download_kbps
                or rate.burst_upload_kbps < rate.upload_kbps
            ):
                errors.append("burst rate must be greater than or equal to the rate")
            if (
                rate.burst_threshold_download_kbps <= 0
                or rate.burst_threshold_upload_kbps <= 0
            ):
                errors.append("burst threshold must be greater than 0")
            if (
                rate.burst_threshold_download_kbps > rate.burst_download_kbps
                or rate.burst_threshold_upload_kbps > rate.burst_upload_kbps
            ):
                errors.append("burst threshold must be less than or equal to the burst rate")
            if rate.burst_time_sec <= 0:
                errors.append("burst time must be greater than 0")

    if not 1 <= rate.priority <= 8:
        errors.append("priority must be between 1 and 8")

    min_values = [getattr(rate, name) for name in _MIN_FIELDS]
    if any(value is not None for value in min_values):
        if any(value is None for value in min_values):
            errors.append("min-rate needs both download and upload")
        else:
            assert rate.min_download_kbps is not None and rate.min_upload_kbps is not None
            if rate.min_download_kbps <= 0 or rate.min_upload_kbps <= 0:
                errors.append("min-rate must be greater than 0")
            if (
                rate.min_download_kbps > rate.download_kbps
                or rate.min_upload_kbps > rate.upload_kbps
            ):
                errors.append("min-rate must be less than or equal to the rate")

    return errors


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def rate_limit_from_fields(values: Mapping[str, Any]) -> RateLimit | None:
    """None when neither download nor upload is set (e.g. the Unlimited preset)."""
    download = values.get("download_kbps")
    upload = values.get("upload_kbps")
    if download is None and upload is None:
        return None
    return RateLimit(
        download_kbps=download or 0,
        upload_kbps=upload or 0,
        burst_download_kbps=values.get("burst_download_kbps"),
        burst_upload_kbps=values.get("burst_upload_kbps"),
        burst_threshold_download_kbps=values.get("burst_threshold_download_kbps"),
        burst_threshold_upload_kbps=values.get("burst_threshold_upload_kbps"),
        burst_time_sec=values.get("burst_time_sec"),
        priority=values.get("priority") or DEFAULT_PRIORITY,
        min_download_kbps=values.get("min_download_kbps"),
        min_upload_kbps=values.get("min_upload_kbps"),
    )


def profile_from_fields(values: Mapping[str, Any]) -> ShapingProfile:
    """Build a ShapingProfile from flat profile fields (schema dump or DB row)."""
    return ShapingProfile(
        service_type=str(_enum_value(values.get("service_type") or "both")),
        rate_limit=rate_limit_from_fields(values),
        session_timeout_sec=values.get("session_timeout_sec"),
        idle_timeout_sec=values.get("idle_timeout_sec"),
        simultaneous_use=values.get("simultaneous_use"),
        mikrotik_group=values.get("mikrotik_group") or None,
        framed_pool=values.get("framed_pool") or None,
        total_quota_bytes=values.get("total_quota_bytes"),
        address_list=values.get("address_list") or None,
        unifi_filter_id=values.get("unifi_filter_id") or None,
    )


def validate_fields(values: Mapping[str, Any]) -> list[str]:
    """Validate flat profile fields (CLAUDE.md 6.1 rules). Empty list == valid."""
    errors: list[str] = []

    service_type = _enum_value(values.get("service_type") or "both")
    if service_type not in SERVICE_TYPES:
        errors.append(f"service_type must be one of {', '.join(SERVICE_TYPES)}")

    download = values.get("download_kbps")
    upload = values.get("upload_kbps")
    if (download is None) != (upload is None):
        errors.append("download and upload rate must be set together")

    has_dependents = any(values.get(name) is not None for name in (*_BURST_FIELDS, *_MIN_FIELDS))
    if has_dependents and download is None and upload is None:
        errors.append("burst and min-rate need a download/upload rate")

    rate = rate_limit_from_fields(values)
    if rate is not None and download is not None and upload is not None:
        errors.extend(validate_rate_limit(rate))
    else:
        priority = values.get("priority") or DEFAULT_PRIORITY
        if not 1 <= priority <= 8:
            errors.append("priority must be between 1 and 8")

    address_list = values.get("address_list")
    if address_list and not ADDRESS_LIST_PATTERN.match(address_list):
        errors.append("address-list must match ^[A-Za-z0-9_-]{1,64}$")

    unifi_filter_id = values.get("unifi_filter_id")
    if unifi_filter_id and not UNIFI_FILTER_ID_PATTERN.match(unifi_filter_id):
        errors.append(
            "unifi_filter_id must be 1-64 characters with no control characters"
        )

    quota = values.get("total_quota_bytes")
    if quota is not None and (
        isinstance(quota, bool) or not isinstance(quota, int) or not 0 < quota <= MAX_QUOTA_BYTES
    ):
        errors.append("quota must be a whole number of bytes greater than 0")

    for name in ("session_timeout_sec", "idle_timeout_sec", "simultaneous_use"):
        value = values.get(name)
        if value is not None and value <= 0:
            errors.append(f"{name} must be greater than 0")

    return errors
