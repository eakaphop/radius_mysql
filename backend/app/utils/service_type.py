"""Service type derived from the group naming convention (CLAUDE.md section 6.1)."""

PPPOE = "pppoe"
HOTSPOT = "hotspot"
UNKNOWN = "unknown"


def service_type_from_groups(groups: list[str]) -> str:
    """`pppoe-<plan>` groups mean PPPoE, `hotspot-<plan>` groups mean Hotspot."""
    if any(group.startswith("pppoe-") for group in groups):
        return PPPOE
    if any(group.startswith("hotspot-") for group in groups):
        return HOTSPOT
    return UNKNOWN
