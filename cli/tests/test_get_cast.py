"""Tests for ``ocmo get cast`` list/show modes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._get_cast_output import (
    GET_CAST_LIST_OUTPUT_KEY,
    CastFormatNotFoundError,
    cast_list_rows,
    cast_show_payload,
)
from ocmo_cli.commands.generated import _execute_generated
from ocmo_cli.main import cli

_SAMPLE_FORMATS = {
    "formats": [
        {
            "format": "json",
            "options_schema": {"type": "object", "properties": {"indent": {"type": "integer"}}},
        },
        {
            "format": "yaml",
            "options_schema": {"type": "object", "properties": {"flow_style": {"type": "string"}}},
        },
    ],
}


def test_cast_list_rows_returns_names_only() -> None:
    assert cast_list_rows(_SAMPLE_FORMATS) == [
        {"format": "json"},
        {"format": "yaml"},
    ]


def test_cast_show_payload_returns_schema() -> None:
    payload = cast_show_payload(_SAMPLE_FORMATS, "yaml")
    assert payload["format"] == "yaml"
    assert "flow_style" in payload["options_schema"]["properties"]


def test_cast_show_payload_is_case_insensitive() -> None:
    payload = cast_show_payload(_SAMPLE_FORMATS, "JSON")
    assert payload["format"] == "json"


def test_cast_show_payload_unknown_format() -> None:
    with pytest.raises(CastFormatNotFoundError):
        cast_show_payload(_SAMPLE_FORMATS, "exe")


def test_execute_generated_get_cast_list(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_call_sdk_method(ctx, op_id, namespace, args, kwargs):
        assert op_id == "list_cast_formats"
        return SimpleNamespace(to_dict=lambda: _SAMPLE_FORMATS)

    monkeypatch.setattr(
        "ocmo_cli.commands.generated._call_sdk_method",
        fake_call_sdk_method,
    )

    ctx = MagicMock()
    ctx.output = None

    _execute_generated(
        ctx=ctx,
        op_ids=["list_cast_formats"],
        action="get",
        resource="cast",
        address=None,
        namespace=None,
        output_fmt="name",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )

    captured = capsys.readouterr()
    assert captured.out == "json\nyaml\n"


def test_execute_generated_get_cast_show_yaml(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_call_sdk_method(ctx, op_id, namespace, args, kwargs):
        assert op_id == "list_cast_formats"
        return SimpleNamespace(to_dict=lambda: _SAMPLE_FORMATS)

    monkeypatch.setattr(
        "ocmo_cli.commands.generated._call_sdk_method",
        fake_call_sdk_method,
    )

    ctx = MagicMock()
    ctx.output = None

    _execute_generated(
        ctx=ctx,
        op_ids=["list_cast_formats"],
        action="get",
        resource="cast",
        address="yaml",
        namespace=None,
        output_fmt="yaml",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )

    captured = capsys.readouterr()
    assert "format: yaml" in captured.out
    assert "flow_style" in captured.out


def test_execute_generated_get_cast_show_rejects_version_suffix() -> None:
    ctx = MagicMock()
    with pytest.raises(SystemExit):
        _execute_generated(
            ctx=ctx,
            op_ids=["list_cast_formats"],
            action="get",
            resource="cast",
            address="yaml@2",
            namespace=None,
            output_fmt=None,
            field=None,
            version_flag=None,
            dry_run=True,
            yes=True,
            file_path=None,
            confirm_mode=None,
        )


def test_get_cast_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "cast", "--help"])
    assert result.exit_code == 0
    assert "ADDRESS" in result.output


def test_get_cast_list_manifest() -> None:
    from ocmo_cli._output_manifest import get_command_spec

    spec = get_command_spec(GET_CAST_LIST_OUTPUT_KEY)
    assert spec.name_field == "format"
    assert spec.table is not None
    assert spec.table.fields == ["format"]
