"""Tests for output formatting."""

from __future__ import annotations

import json

import pytest

from ocmo_cli._output import as_dict, emit, extract_field, sanitize_for_output


def test_emit_name_only_names(capsys: pytest.CaptureFixture[str]) -> None:
    emit([{"name": "web", "path": "app/web"}, {"name": "api", "path": "app/api"}], "name")
    assert capsys.readouterr().out == "web\napi\n"


def test_emit_path_only_paths(capsys: pytest.CaptureFixture[str]) -> None:
    emit([{"name": "web", "path": "app/web"}], "path")
    assert capsys.readouterr().out == "app/web\n"


def test_emit_jsonpath_list(capsys: pytest.CaptureFixture[str]) -> None:
    data = [
        {"name": "a", "meta": {"version": 1}},
        {"name": "b", "meta": {"version": 2}},
    ]
    emit(data, "jsonpath=meta.version")
    assert capsys.readouterr().out == "1\n2\n"


def test_extract_field_list(capsys: pytest.CaptureFixture[str]) -> None:
    data = [{"version_data": {"data": {"x": 1}}}, {"version_data": {"data": {"x": 2}}}]
    extract_field(data, "version_data.data.x")
    assert capsys.readouterr().out == "1\n2\n"


def test_emit_table_uses_nonempty_columns(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ocmo_cli._output.sys.stdout.isatty", lambda: False)
    emit(
        [
            {"name": "web", "path": "app/web", "tags": []},
            {"name": "api", "path": "app/api", "tags": ["prod"]},
        ],
        "table",
    )
    out = capsys.readouterr().out
    assert "NAME" in out
    assert "PATH" in out
    assert "TAGS" in out


def test_emit_table_user_details_as_yaml(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ocmo_cli._output.sys.stdout.isatty", lambda: False)
    emit(
        {
            "auth_type": "user",
            "identifier": "user-001",
            "user_details": {
                "email": "admin@example.com",
                "is_global_admin": True,
            },
        },
        "table",
    )
    out = capsys.readouterr().out
    assert "USER_DETAILS" in out
    assert "email: admin@example.com" in out
    assert "is_global_admin: true" in out


def test_emit_table_resolver_details_as_yaml(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ocmo_cli._output.sys.stdout.isatty", lambda: False)
    emit(
        {
            "auth_type": "resolver",
            "identifier": "app/svc",
            "resolver_details": {
                "namespace": "my-ns",
                "name": "svc",
                "token_number": 1,
            },
        },
        "table",
    )
    out = capsys.readouterr().out
    assert "RESOLVER_DETAILS" in out
    assert "namespace: my-ns" in out
    assert "token_number: 1" in out


def test_emit_table_structured_list_column_as_yaml(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ocmo_cli._output.sys.stdout.isatty", lambda: False)
    emit([{"name": "cfg", "tags": ["prod", "stable"]}], "table")
    out = capsys.readouterr().out
    assert "TAGS" in out
    assert "prod, stable" in out
    assert "- prod" not in out


def test_emit_table_formats_iso_datetime_strings(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ocmo_cli._output.sys.stdout.isatty", lambda: False)
    emit(
        [{"version": 1, "updated_at": "2026-08-08T10:43:32.484000+00:00"}],
        "table",
    )
    out = capsys.readouterr().out
    assert "UPDATED_AT" in out
    assert "T10:43" not in out
    assert ":43:32" in out


def test_emit_json(capsys: pytest.CaptureFixture[str]) -> None:
    emit({"a": 1}, "json")
    assert json.loads(capsys.readouterr().out) == {"a": 1}


def test_emit_json_keeps_iso_datetime_strings(capsys: pytest.CaptureFixture[str]) -> None:
    iso = "2026-08-08T10:43:32.484000+00:00"
    emit({"updated_at": iso}, "json")
    assert json.loads(capsys.readouterr().out)["updated_at"] == iso


def test_sanitize_strips_private_keys() -> None:
    assert sanitize_for_output({"name": "x", "_http": object()}) == {"name": "x"}


def test_sanitize_strips_internal_ids() -> None:
    assert sanitize_for_output({"id": 42, "path": "app/web", "namespace_id": 1}) == {
        "path": "app/web",
    }


def test_sanitize_keeps_public_string_ids() -> None:
    event_id = "550e8400-e29b-41d4-a716-446655440000"
    assert sanitize_for_output({"id": event_id, "operation": "Read config"}) == {
        "id": event_id,
        "operation": "Read config",
    }


class _ToDictModel:
    def to_dict(self) -> dict[str, object]:
        return {"name": "x"}


def test_as_dict_from_to_dict() -> None:
    assert as_dict(_ToDictModel()) == {"name": "x"}


def test_as_dict_plain_dict() -> None:
    assert as_dict({"a": 1}) == {"a": 1}


def test_as_dict_vars_fallback() -> None:
    class Plain:
        def __init__(self) -> None:
            self.value = 42

    assert as_dict(Plain()) == {"value": 42}


def test_as_dict_non_dict_to_dict_returns_empty() -> None:
    class Bad:
        def to_dict(self) -> list[str]:
            return ["nope"]

    assert as_dict(Bad(), fallback_vars=False) == {}
