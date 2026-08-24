"""Tests for get command output formatting."""

from __future__ import annotations

import pytest

from ocmo_cli._output_manifest import emit_command_output

_SAMPLE_NAMESPACES = [
    {
        "name": "prod",
        "description": "Production",
        "permissions_tag": "latest",
        "webhooks_tag": "v2",
        "git_sync_tag": "latest",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-02-01T00:00:00+00:00",
    },
    {
        "name": "dev",
        "description": "",
        "permissions_tag": "latest",
        "webhooks_tag": "latest",
        "git_sync_tag": "latest",
        "created_at": "2026-01-02T00:00:00+00:00",
        "updated_at": "2026-01-02T00:00:00+00:00",
    },
]


def test_emit_namespace_table_shows_name_and_description_only(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ocmo_cli._output.sys.stdout.isatty", lambda: False)
    emit_command_output("get namespace", _SAMPLE_NAMESPACES, "table")
    out = capsys.readouterr().out
    assert "NAME" in out
    assert "DESCRIPTION" in out
    assert "prod" in out
    assert "Production" in out
    assert "PERMISSIONS_TAG" not in out
    assert "CREATED_AT" not in out


def test_emit_namespace_wide_shows_all_fields(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ocmo_cli._output.sys.stdout.isatty", lambda: False)
    emit_command_output("get namespace", _SAMPLE_NAMESPACES, "wide")
    out = capsys.readouterr().out
    for col in (
        "NAME",
        "DESCRIPTION",
        "PERMISSIONS_TAG",
        "WEBHOOKS_TAG",
        "GIT_SYNC_TAG",
        "CREATED_AT",
        "UPDATED_AT",
    ):
        assert col in out
    assert "v2" in out


def test_emit_namespace_show_single_row_table(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ocmo_cli._output.sys.stdout.isatty", lambda: False)
    emit_command_output("get namespace", _SAMPLE_NAMESPACES[0], "table")
    out = capsys.readouterr().out
    assert "NAME" in out
    assert "DESCRIPTION" in out
    assert "prod" in out
    assert "PERMISSIONS_TAG" not in out
