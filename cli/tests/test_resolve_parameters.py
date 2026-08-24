"""Tests for ``ocmo resolve parameters`` output."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._output_manifest import emit_command_output, get_command_spec
from ocmo_cli._resolve_parameters_output import (
    filter_parameters_data,
    parameter_config_value,
    parameter_resolved_value,
    resolve_parameters_table_rows,
)
from ocmo_cli.commands.resolve_parameters import resolve_parameters_cmd
from ocmo_cli.main import cli

_SAMPLE_RESPONSE = {
    "path": "app/web",
    "version": 3,
    "requested_version": "latest",
    "parameters": {
        "host": {
            "type": "projected",
            "description": "Config name",
            "selector": ".Name",
            "raw_value": "web",
            "effective_value": "web",
            "transformers_applied": ["lower"],
        },
        "replicas": {
            "type": "dynamic",
            "description": "Replica count",
            "declared_default": 2,
            "caller_supplied": False,
            "effective_value": 2,
            "transformers_applied": [],
        },
        "cred": {
            "type": "secret",
            "description": "API credential",
            "secret_reference": "../../shared/secret@latest",
            "effective_value": "***",
            "transformers_applied": ["b64_encode"],
        },
    },
}


def test_resolve_parameters_spec_defaults_to_table_on_tty() -> None:
    spec = get_command_spec("resolve parameters")
    assert spec.default_tty == "table"
    assert spec.default_non_tty == "yaml"
    assert "table" in spec.supported_formats
    assert "raw" not in spec.supported_formats
    assert spec.table is not None
    assert spec.table.fields == [
        "name",
        "type",
        "value",
        "resolved_value",
        "description",
        "transformers",
    ]


@pytest.mark.parametrize(
    ("param", "expected"),
    [
        ({"type": "projected", "selector": ".Name"}, ".Name"),
        ({"type": "dynamic", "declared_default": 2}, 2),
        ({"type": "secret", "secret_reference": "shared/secret@latest"}, "shared/secret@latest"),
    ],
)
def test_parameter_config_value_by_type(param: dict, expected: object) -> None:
    assert parameter_config_value(param) == expected


def test_parameter_resolved_value_uses_effective_value() -> None:
    assert parameter_resolved_value({"effective_value": "***"}) == "***"


def test_filter_parameters_data_by_type() -> None:
    filtered = filter_parameters_data(_SAMPLE_RESPONSE, ("secret",))
    rows = resolve_parameters_table_rows(filtered)
    assert [row["name"] for row in rows] == ["cred"]
    assert rows[0]["type"] == "secret"

    multi = filter_parameters_data(_SAMPLE_RESPONSE, ("projected", "dynamic"))
    assert set(multi["parameters"]) == {"host", "replicas"}


def test_filter_parameters_data_without_types_returns_unchanged() -> None:
    assert filter_parameters_data(_SAMPLE_RESPONSE, ()) is _SAMPLE_RESPONSE


def test_resolve_parameters_table_rows_flattens_parameters() -> None:
    rows = resolve_parameters_table_rows(_SAMPLE_RESPONSE)
    assert [row["name"] for row in rows] == ["cred", "host", "replicas"]

    host = next(row for row in rows if row["name"] == "host")
    assert host["type"] == "projected"
    assert host["value"] == ".Name"
    assert host["resolved_value"] == "web"
    assert host["description"] == "Config name"
    assert host["transformers"] == "lower"

    replicas = next(row for row in rows if row["name"] == "replicas")
    assert replicas["value"] == 2
    assert replicas["resolved_value"] == 2
    assert replicas["transformers"] == ""

    cred = next(row for row in rows if row["name"] == "cred")
    assert cred["value"] == "../../shared/secret@latest"
    assert cred["resolved_value"] == "***"
    assert cred["transformers"] == "b64_encode"


def test_emit_command_output_resolve_parameters_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_command_output("resolve parameters", _SAMPLE_RESPONSE, "table")
    out = capsys.readouterr().out
    assert "NAME" in out
    assert "RESOLVED_VALUE" in out
    assert "TRANSFORMERS" in out
    assert "host" in out
    assert ".Name" in out
    assert "b64_encode" in out
    assert "parameters" not in out


def test_resolve_parameters_help_lists_expected_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "parameters", "--help"])
    assert result.exit_code == 0, result.output
    assert "--type" in result.output
    assert "projected" in result.output
    assert "dynamic" in result.output
    assert "secret" in result.output
    assert "--no-creds" not in result.output
    assert "-o" in result.output or "--output" in result.output
    assert "table" in result.output
    assert "--field" not in result.output
    assert "--file" not in result.output


def test_resolve_parameters_rejects_raw_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["-n", "prod", "resolve", "parameters", "app/web", "-o", "raw"],
    )
    assert result.exit_code != 0
    assert "not a valid output format" in result.output


def test_resolve_parameters_calls_sdk_and_prints_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = MagicMock()
    view.resolve_parameters.return_value = _SAMPLE_RESPONSE

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.output = None

    monkeypatch.setattr(
        "ocmo_cli.commands.resolve_parameters.parse_address_or_exit",
        lambda _address, version_flag=None: ("app/web", None),
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            resolve_parameters_cmd,
            ["app/web", "-o", "table"],
            obj=ctx,
        )

    assert result.exit_code == 0, result.output
    view.resolve_parameters.assert_called_once_with("app/web")
    assert "NAME" in result.output
    assert "host" in result.output
    assert "cred" in result.output
    assert "RESOLVED_VALUE" in result.output


def test_resolve_parameters_type_filter_applies_to_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = MagicMock()
    view.resolve_parameters.return_value = _SAMPLE_RESPONSE

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.output = None

    monkeypatch.setattr(
        "ocmo_cli.commands.resolve_parameters.parse_address_or_exit",
        lambda _address, version_flag=None: ("app/web", None),
    )

    runner = CliRunner()
    result = runner.invoke(
        resolve_parameters_cmd,
        ["app/web", "-o", "table", "--type", "dynamic"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "replicas" in result.output
    assert "host" not in result.output
    assert "cred" not in result.output
