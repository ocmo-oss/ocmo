"""Tests for SDK error formatting."""

from __future__ import annotations

import pytest
from ocmo.errors import OcmoValidationError

from ocmo_cli._errors import _format_validation_errors, handle_sdk_error


def test_format_validation_errors_lists_fields() -> None:
    detail = _format_validation_errors(
        [
            {"loc": ["body", "namespace"], "msg": "Field required"},
            {"loc": ["body", "reason"], "msg": "Field required"},
        ]
    )
    assert "namespace: Field required" in detail
    assert "reason: Field required" in detail


def test_format_validation_errors_accepts_api_strings() -> None:
    detail = _format_validation_errors(
        [
            "name: Field required",
            "query.limit: Input should be a valid integer, unable to parse string as an integer",
        ]
    )
    assert "name: Field required" in detail
    assert "query.limit" in detail


def test_validation_error_shows_detail_once(capsys: pytest.CaptureFixture[str]) -> None:
    exc = OcmoValidationError(
        "This field cannot be blank.",
        errors=["This field cannot be blank."],
        status_code=422,
        method="POST",
        path="/api/v1/ns/",
    )
    with pytest.raises(SystemExit):
        handle_sdk_error(exc)
    err = capsys.readouterr().err
    assert err.count("This field cannot be blank.") == 1


def test_validation_error_starts_detail_on_new_line(capsys: pytest.CaptureFixture[str]) -> None:
    exc = OcmoValidationError(
        "name: Namespace with this Name already exists.",
        errors=["name: Namespace with this Name already exists."],
        status_code=422,
        method="POST",
        path="/api/v1/ns/",
    )
    with pytest.raises(SystemExit):
        handle_sdk_error(exc)
    err = capsys.readouterr().err
    assert err == ("Error:\n" "  - name: Namespace with this Name already exists.\n")


def test_handle_sdk_validation_error_includes_details(capsys: pytest.CaptureFixture[str]) -> None:
    exc = OcmoValidationError(
        "name: Field required; description: Field required",
        errors=["name: Field required", "description: Field required"],
        status_code=422,
        method="POST",
        path="/api/v1/ns/",
    )
    with pytest.raises(SystemExit):
        handle_sdk_error(exc)
    err = capsys.readouterr().err
    assert "name: Field required" in err
    assert "description: Field required" in err
    assert err.count("Field required") == 2
