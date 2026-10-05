"""The single place that decides whether a radacct session is PPPoE or Hotspot
(CLAUDE.md section 6.1). The Python and SQL forms below must stay equivalent.

Rules (MikroTik): PPPoE sessions carry Framed-Protocol=PPP / Service-Type=
Framed-User and often NAS-Port-Type=Virtual or Ethernet; Hotspot sessions carry
Service-Type=Login-User and often NAS-Port-Type=Wireless-802.11 or Ethernet.
Ethernet alone is ambiguous, so it is never used on its own. Verify these
against real radacct rows (docs/environment.md TODO).
"""

from sqlalchemy import and_, func, not_, or_
from sqlalchemy.sql.elements import ColumnElement

from app.db.models.radius import RadAcct
from app.utils.service_type import HOTSPOT, PPPOE, UNKNOWN


def classify_session(
    *, nasporttype: str | None, servicetype: str | None, framedprotocol: str | None
) -> str:
    if framedprotocol == "PPP" or servicetype == "Framed-User" or nasporttype == "Virtual":
        return PPPOE
    if servicetype == "Login-User" or nasporttype == "Wireless-802.11":
        return HOTSPOT
    return UNKNOWN


def _is_pppoe() -> ColumnElement[bool]:
    return or_(
        func.coalesce(RadAcct.framedprotocol, "") == "PPP",
        func.coalesce(RadAcct.servicetype, "") == "Framed-User",
        func.coalesce(RadAcct.nasporttype, "") == "Virtual",
    )


def _is_hotspot() -> ColumnElement[bool]:
    return and_(
        not_(_is_pppoe()),
        or_(
            func.coalesce(RadAcct.servicetype, "") == "Login-User",
            func.coalesce(RadAcct.nasporttype, "") == "Wireless-802.11",
        ),
    )


def service_filter(service: str) -> ColumnElement[bool] | None:
    """SQL condition selecting sessions of `service`; None means no filter."""
    if service == PPPOE:
        return _is_pppoe()
    if service == HOTSPOT:
        return _is_hotspot()
    return None
