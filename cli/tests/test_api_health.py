"""Tests for ``ocmo api-health``."""

from __future__ import annotations

from click.testing import CliRunner

from ocmo_cli._output_manifest import get_command_spec
from ocmo_cli.main import cli


def test_api_health_manifest_spec() -> None:
    spec = get_command_spec("api-health")
    assert "table" in spec.supported_formats
    assert "yaml" in spec.supported_formats


def test_api_health_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["api-health", "--help"])
    assert result.exit_code == 0
    assert "dependency health" in result.output.lower()


def test_get_health_no_longer_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "health"])
    assert result.exit_code != 0
