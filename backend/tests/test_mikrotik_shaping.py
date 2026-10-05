"""Unit tests for services/mikrotik_shaping — the rx/tx order bug lives here."""

from dataclasses import replace

import pytest

from app.services.mikrotik_shaping import (
    RateLimit,
    RateLimitParseError,
    build_attributes,
    build_rate_limit,
    parse_rate_limit,
    profile_from_fields,
    split_quota,
    validate_fields,
    validate_rate_limit,
)

SPEC_BURST = RateLimit(
    download_kbps=20000,
    upload_kbps=5000,
    burst_download_kbps=40000,
    burst_upload_kbps=10000,
    burst_threshold_download_kbps=15000,
    burst_threshold_upload_kbps=4000,
    burst_time_sec=10,
    priority=5,
)


# ---------------------------------------------------------------- CLAUDE.md 6.1 examples


def test_spec_example_plain_rate_is_upload_then_download() -> None:
    # 20M down / 5M up -> "5M/20M" (rx = upload first).
    assert build_rate_limit(RateLimit(download_kbps=20000, upload_kbps=5000)) == "5M/20M"


def test_spec_example_burst_threshold_time_priority() -> None:
    assert build_rate_limit(SPEC_BURST) == "5M/20M 10M/40M 4M/15M 10/10 5"


def test_spec_example_with_min_rate() -> None:
    rate = replace(SPEC_BURST, min_download_kbps=8000, min_upload_kbps=2000)
    assert build_rate_limit(rate) == "5M/20M 10M/40M 4M/15M 10/10 5 2M/8M"


# ---------------------------------------------------------------------------- build


def test_download_and_upload_are_never_swapped() -> None:
    value = build_rate_limit(RateLimit(download_kbps=100000, upload_kbps=1000))
    upload, download = value.split("/")
    assert upload == "1M"
    assert download == "100M"


def test_uses_k_when_not_divisible_by_1000() -> None:
    assert build_rate_limit(RateLimit(download_kbps=1500, upload_kbps=512)) == "512k/1500k"


def test_burst_with_default_priority_omits_priority() -> None:
    rate = replace(SPEC_BURST, priority=8)
    assert build_rate_limit(rate) == "5M/20M 10M/40M 4M/15M 10/10"


def test_priority_without_burst_fills_earlier_segments_with_the_rate() -> None:
    rate = RateLimit(download_kbps=20000, upload_kbps=5000, priority=3)
    assert build_rate_limit(rate) == "5M/20M 5M/20M 5M/20M 0/0 3"


def test_min_rate_without_priority_still_writes_default_priority() -> None:
    rate = RateLimit(
        download_kbps=20000, upload_kbps=5000, min_download_kbps=8000, min_upload_kbps=2000
    )
    assert build_rate_limit(rate) == "5M/20M 5M/20M 5M/20M 0/0 8 2M/8M"


# ---------------------------------------------------------------------------- parse


def test_parse_single_value_applies_to_both_directions() -> None:
    rate = parse_rate_limit("10M")
    assert (rate.upload_kbps, rate.download_kbps) == (10000, 10000)


def test_parse_mixed_units() -> None:
    rate = parse_rate_limit("512k/2M")
    assert rate.upload_kbps == 512
    assert rate.download_kbps == 2000


def test_parse_plain_numbers_are_bps() -> None:
    rate = parse_rate_limit("1000000/2000000")
    assert rate.upload_kbps == 1000
    assert rate.download_kbps == 2000


def test_parse_decimal_and_gigabit() -> None:
    rate = parse_rate_limit("1.5M/1G")
    assert rate.upload_kbps == 1500
    assert rate.download_kbps == 1_000_000


def test_parse_burst_time_with_seconds_suffix() -> None:
    rate = parse_rate_limit("5M/20M 10M/40M 4M/15M 10s/10s 5")
    assert rate.burst_time_sec == 10
    assert rate.priority == 5


def test_parse_partial_burst_keeps_what_is_there() -> None:
    rate = parse_rate_limit("5M/20M 10M/40M")
    assert rate.burst_download_kbps == 40000
    assert rate.burst_threshold_download_kbps is None


@pytest.mark.parametrize("value", ["", "abc", "5M/20M/1M", "1 2 3 4 5 6 7", "5X/20M"])
def test_parse_rejects_malformed(value: str) -> None:
    with pytest.raises(RateLimitParseError):
        parse_rate_limit(value)


ROUND_TRIP_CASES = [
    RateLimit(download_kbps=20000, upload_kbps=5000),
    RateLimit(download_kbps=1500, upload_kbps=512),
    SPEC_BURST,
    replace(SPEC_BURST, priority=8),
    replace(SPEC_BURST, min_download_kbps=8000, min_upload_kbps=2000),
    RateLimit(download_kbps=20000, upload_kbps=5000, priority=1),
    RateLimit(
        download_kbps=20000, upload_kbps=5000, min_download_kbps=8000, min_upload_kbps=2000
    ),
    RateLimit(
        download_kbps=30500,
        upload_kbps=10250,
        burst_download_kbps=61000,
        burst_upload_kbps=20500,
        burst_threshold_download_kbps=22875,
        burst_threshold_upload_kbps=7687,
        burst_time_sec=16,
        priority=2,
        min_download_kbps=1000,
        min_upload_kbps=512,
    ),
]


@pytest.mark.parametrize("rate", ROUND_TRIP_CASES)
def test_round_trip(rate: RateLimit) -> None:
    assert validate_rate_limit(rate) == []
    assert parse_rate_limit(build_rate_limit(rate)) == rate


# ------------------------------------------------------------------------- validate


def test_burst_below_rate_is_invalid() -> None:
    errors = validate_rate_limit(replace(SPEC_BURST, burst_download_kbps=10000))
    assert any("burst rate" in error for error in errors)


def test_threshold_above_burst_is_invalid() -> None:
    errors = validate_rate_limit(replace(SPEC_BURST, burst_threshold_download_kbps=50000))
    assert any("threshold" in error for error in errors)


def test_min_above_rate_is_invalid() -> None:
    rate = replace(SPEC_BURST, min_download_kbps=30000, min_upload_kbps=2000)
    assert any("min-rate" in error for error in validate_rate_limit(rate))


def test_incomplete_burst_is_invalid() -> None:
    rate = RateLimit(download_kbps=20000, upload_kbps=5000, burst_download_kbps=40000)
    assert validate_rate_limit(rate)


def test_priority_out_of_range_is_invalid() -> None:
    assert validate_rate_limit(RateLimit(download_kbps=1000, upload_kbps=1000, priority=9))


def test_validate_fields_unlimited_is_valid() -> None:
    assert validate_fields({"service_type": "both"}) == []


def test_validate_fields_requires_both_directions() -> None:
    assert validate_fields({"download_kbps": 1000})


def test_validate_fields_burst_without_rate() -> None:
    assert validate_fields({"burst_download_kbps": 1000})


@pytest.mark.parametrize("value", ["has space", "semi;colon", "x" * 65])
def test_validate_fields_address_list_pattern(value: str) -> None:
    assert validate_fields({"address_list": value})


@pytest.mark.parametrize("value", ["10M-5M plan", "unlimited"])
def test_validate_fields_unifi_filter_id_allows_free_text(value: str) -> None:
    assert validate_fields({"unifi_filter_id": value}) == []


@pytest.mark.parametrize("value", ["x" * 65, "bad\x00value", "\x7f"])
def test_validate_fields_unifi_filter_id_rejects_control_chars_and_overlong(value: str) -> None:
    assert validate_fields({"unifi_filter_id": value})


def test_validate_fields_quota_must_be_positive_integer() -> None:
    assert validate_fields({"total_quota_bytes": 0})
    assert validate_fields({"total_quota_bytes": 1.5})
    assert validate_fields({"total_quota_bytes": 10**9}) == []


# ------------------------------------------------------------------------ attributes


def test_split_quota_into_low_and_gigawords() -> None:
    assert split_quota(5 * 2**30) == (2**30, 1)
    assert split_quota(1000) == (1000, 0)


def _attrs(values: dict[str, object]) -> dict[str, str]:
    result = build_attributes(profile_from_fields(values))
    return {name: value for name, _, value in result.reply}


def test_pppoe_profile_attributes() -> None:
    reply = _attrs(
        {
            "service_type": "pppoe",
            "download_kbps": 30000,
            "upload_kbps": 10000,
            "framed_pool": "pool1",
            "mikrotik_group": "pppoe-standard",
            "total_quota_bytes": 5 * 2**30,
            "address_list": "premium",
        }
    )
    assert reply["Mikrotik-Rate-Limit"] == "10M/30M"
    assert reply["Framed-Pool"] == "pool1"
    assert reply["Mikrotik-Group"] == "pppoe-standard"
    assert reply["Mikrotik-Total-Limit"] == str(2**30)
    assert reply["Mikrotik-Total-Limit-Gigawords"] == "1"
    assert reply["Mikrotik-Address-List"] == "premium"
    assert reply["Acct-Interim-Interval"] == "300"
    assert "WISPr-Bandwidth-Max-Down" not in reply


def test_hotspot_profile_adds_wispr_and_skips_framed_pool() -> None:
    reply = _attrs(
        {
            "service_type": "hotspot",
            "download_kbps": 10000,
            "upload_kbps": 5000,
            "framed_pool": "pool1",
            "idle_timeout_sec": 600,
        }
    )
    assert reply["WISPr-Bandwidth-Max-Down"] == "10000000"
    assert reply["WISPr-Bandwidth-Max-Up"] == "5000000"
    assert reply["Idle-Timeout"] == "600"
    assert "Framed-Pool" not in reply


def test_unlimited_profile_has_no_rate_limit() -> None:
    result = build_attributes(profile_from_fields({"service_type": "both"}))
    assert result.rate_limit_string is None
    assert all(name != "Mikrotik-Rate-Limit" for name, _, _ in result.reply)


def test_simultaneous_use_is_a_check_attribute() -> None:
    result = build_attributes(profile_from_fields({"simultaneous_use": 2}))
    assert result.check == [("Simultaneous-Use", ":=", "2")]
    assert all(name != "Simultaneous-Use" for name, _, _ in result.reply)


def test_unifi_filter_id_becomes_filter_id_attribute() -> None:
    reply = _attrs({"unifi_filter_id": "10M-5M"})
    assert reply["Filter-Id"] == "10M-5M"
    assert "Mikrotik-Rate-Limit" not in reply


def test_all_generated_attributes_use_set_operator() -> None:
    result = build_attributes(
        profile_from_fields(
            {"download_kbps": 1000, "upload_kbps": 1000, "session_timeout_sec": 3600}
        )
    )
    assert {op for _, op, _ in result.reply} == {":="}
