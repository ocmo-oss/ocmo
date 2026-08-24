"""Tests for ``ocmo schema`` command."""

from __future__ import annotations

from click.testing import CliRunner

from ocmo_cli._output_manifest import get_command_spec
from ocmo_cli.main import cli


def test_schema_spec_supports_only_json_and_yaml() -> None:
    spec = get_command_spec("schema")
    assert spec.supported_formats == ("json", "yaml")
    assert "table" not in spec.supported_formats


def test_explain_command_removed() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["explain", "--help"])
    assert result.exit_code != 0


def test_schema_help_shows_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["schema", "--help"])
    assert result.exit_code == 0, result.output
    assert "RESOURCE" in result.output
    assert "-o" in result.output or "--output" in result.output


def test_schema_cli_rejects_table_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["schema", "ocmo", "-o", "table"])
    assert result.exit_code != 0
    assert "not a valid output format" in result.output


def test_schema_config_requires_address() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["schema", "config"])
    assert result.exit_code != 0
    assert "ADDRESS is required" in result.output


def test_schema_ocmo_rejects_address() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["schema", "ocmo", "app/web"])
    assert result.exit_code != 0
    assert "ADDRESS is not used" in result.output
