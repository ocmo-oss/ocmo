"""Tests for output datetime formatting."""

from __future__ import annotations

import datetime

from ocmo_cli._output import format_datetime


def test_format_datetime_current_year_omits_year() -> None:
    now = datetime.datetime.now().astimezone()
    value = now.replace(hour=14, minute=13, second=27, microsecond=0)
    result = format_datetime(value)
    assert "May" in result or now.strftime("%b") in result
    assert "14:13:27" in result
    assert f", {now.year}," not in result


def test_format_datetime_other_year_includes_year() -> None:
    now = datetime.datetime.now().astimezone()
    other_year = now.year - 1
    value = now.replace(year=other_year, hour=14, minute=13, second=27, microsecond=0)
    result = format_datetime(value)
    assert f", {other_year}," in result
    assert "14:13:27" in result
