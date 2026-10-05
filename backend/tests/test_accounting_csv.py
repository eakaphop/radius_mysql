"""Unit tests for the CSV export cell rendering."""

from datetime import datetime

import pytest

from app.services.accounting_service import csv_cell


def test_none_is_empty() -> None:
    assert csv_cell(None) == ""


def test_numbers_are_not_prefixed_even_when_negative() -> None:
    assert csv_cell(-5) == "-5"
    assert csv_cell(12345) == "12345"


def test_datetime_is_iso() -> None:
    assert csv_cell(datetime(2026, 9, 13, 10, 30)) == "2026-09-13 10:30:00"


@pytest.mark.parametrize("value", ["=SUM(A1)", "+1", "-1", "@cmd", "\tx"])
def test_formula_like_strings_are_neutralised(value: str) -> None:
    assert csv_cell(value) == "'" + value


def test_plain_strings_pass_through() -> None:
    assert csv_cell("bob") == "bob"
