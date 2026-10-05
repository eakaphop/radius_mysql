"""Unit tests for services/session_classifier (Python form)."""

import pytest

from app.services.session_classifier import classify_session


@pytest.mark.parametrize(
    ("nasporttype", "servicetype", "framedprotocol"),
    [
        ("Ethernet", "Framed-User", "PPP"),
        ("Virtual", None, None),
        ("Ethernet", None, "PPP"),
        (None, "Framed-User", None),
    ],
)
def test_pppoe_sessions(
    nasporttype: str | None, servicetype: str | None, framedprotocol: str | None
) -> None:
    assert (
        classify_session(
            nasporttype=nasporttype, servicetype=servicetype, framedprotocol=framedprotocol
        )
        == "pppoe"
    )


@pytest.mark.parametrize(
    ("nasporttype", "servicetype"),
    [
        ("Wireless-802.11", None),
        ("Ethernet", "Login-User"),
        ("Wireless-802.11", "Login-User"),
    ],
)
def test_hotspot_sessions(nasporttype: str | None, servicetype: str | None) -> None:
    assert (
        classify_session(nasporttype=nasporttype, servicetype=servicetype, framedprotocol=None)
        == "hotspot"
    )


def test_ethernet_alone_is_unknown() -> None:
    assert (
        classify_session(nasporttype="Ethernet", servicetype=None, framedprotocol=None)
        == "unknown"
    )


def test_ppp_wins_over_wireless_port_type() -> None:
    assert (
        classify_session(nasporttype="Wireless-802.11", servicetype=None, framedprotocol="PPP")
        == "pppoe"
    )
