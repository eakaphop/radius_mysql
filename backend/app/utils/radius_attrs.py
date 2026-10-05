"""Whitelist of RADIUS attributes and operators accepted by the API.

Extend the sets below when a new attribute is needed — validation is driven
by this module alone, never by hardcoding names into Pydantic schemas.
"""

# Operators supported by FreeRADIUS's SQL attribute tables (CLAUDE.md section 5).
ALLOWED_OPERATORS: frozenset[str] = frozenset(
    {":=", "==", "=", "+=", "!=", ">", ">=", "<", "<=", "=~", "!~", "=*", "!*"}
)

# Attributes valid in radcheck / radgroupcheck (authorisation checks).
CHECK_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "Cleartext-Password",
        "SSHA-Password",
        "NT-Password",
        "MD5-Password",
        "Crypt-Password",
        "Auth-Type",
        "Expiration",
        "Simultaneous-Use",
        "Login-Time",
        "Calling-Station-Id",
        "Called-Station-Id",
        "NAS-IP-Address",
        "Pool-Name",
    }
)

# Attributes valid in radreply / radgroupreply (values returned to the NAS).
REPLY_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "Session-Timeout",
        "Idle-Timeout",
        "Acct-Interim-Interval",
        "Port-Limit",
        "Service-Type",
        "Framed-Protocol",
        "Framed-IP-Address",
        "Framed-IP-Netmask",
        "Framed-Pool",
        "Framed-Route",
        "Framed-MTU",
        "Reply-Message",
        "Filter-Id",
        "Class",
        # MikroTik VSAs (vendor 14988) — see CLAUDE.md section 6.1
        "Mikrotik-Rate-Limit",
        "Mikrotik-Address-List",
        "Mikrotik-Group",
        "Mikrotik-Total-Limit",
        "Mikrotik-Total-Limit-Gigawords",
        "Mikrotik-Recv-Limit",
        "Mikrotik-Recv-Limit-Gigawords",
        "Mikrotik-Xmit-Limit",
        "Mikrotik-Xmit-Limit-Gigawords",
        "Mikrotik-Wireless-Forward",
        "Mikrotik-Wireless-Comment",
        # WISPr (hotspot fallback)
        "WISPr-Bandwidth-Max-Down",
        "WISPr-Bandwidth-Max-Up",
        "WISPr-Session-Terminate-Time",
    }
)

# Password attributes are never returned through the API (CLAUDE.md section 8).
PASSWORD_ATTRIBUTES: frozenset[str] = frozenset(
    {"Cleartext-Password", "SSHA-Password", "NT-Password", "MD5-Password", "Crypt-Password"}
)

DISABLED_ATTRIBUTE = "Auth-Type"
DISABLED_VALUE = "Reject"
EXPIRATION_ATTRIBUTE = "Expiration"


def is_valid_operator(op: str) -> bool:
    return op in ALLOWED_OPERATORS


def is_valid_check_attribute(attribute: str) -> bool:
    return attribute in CHECK_ATTRIBUTES


def is_valid_reply_attribute(attribute: str) -> bool:
    return attribute in REPLY_ATTRIBUTES
