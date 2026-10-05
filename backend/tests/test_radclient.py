"""Unit tests for services/radclient request building and output parsing."""

import pytest

from app.services.radclient import (
    InvalidAttributeValueError,
    build_request_body,
    parse_radclient_output,
    quote_value,
)


def test_quote_value_escapes_quotes_and_backslashes() -> None:
    assert quote_value('a"b\\c') == '"a\\"b\\\\c"'


@pytest.mark.parametrize("value", ["line\nbreak", "carriage\rreturn", "nul\0byte"])
def test_quote_value_rejects_attribute_injection(value: str) -> None:
    with pytest.raises(InvalidAttributeValueError):
        quote_value(value)


def test_build_request_body() -> None:
    body = build_request_body([("User-Name", "bob"), ("Mikrotik-Rate-Limit", "5M/20M")])
    assert body == 'User-Name = "bob"\nMikrotik-Rate-Limit = "5M/20M"\n'


def test_parse_ack() -> None:
    output = (
        "Sent CoA-Request Id 12 from 0.0.0.0:40000 to 10.0.0.1:3799 length 60\n"
        "Received CoA-ACK Id 12 from 10.0.0.1:3799 to 0.0.0.0:40000 length 20\n"
    )
    result = parse_radclient_output(output)
    assert result.success
    assert result.response == "CoA-ACK"
    assert result.error_cause is None


def test_parse_nak_with_error_cause() -> None:
    output = (
        "Sent Disconnect-Request Id 7 from 0.0.0.0:40000 to 10.0.0.1:3799 length 60\n"
        "Received Disconnect-NAK Id 7 from 10.0.0.1:3799 to 0.0.0.0:40000 length 26\n"
        "\tError-Cause = Session-Context-Not-Found\n"
    )
    result = parse_radclient_output(output)
    assert not result.success
    assert result.response == "Disconnect-NAK"
    assert result.error_cause == "Session-Context-Not-Found"
    assert "Session-Context-Not-Found" in result.detail


def test_parse_no_response() -> None:
    result = parse_radclient_output("(0) No reply from server for ID 12 socket 3\n")
    assert not result.success
    assert result.response is None
