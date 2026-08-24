"""Tests for ocmo can-i output formats."""

from __future__ import annotations

import click
import pytest
from click.testing import CliRunner

from ocmo_cli._output_manifest import get_command_spec, validate_output_format
from ocmo_cli.main import cli


@pytest.mark.parametrize("fmt", ("wide", "name", "path", "raw"))
def test_can_i_manifest_rejects_unsupported(fmt: str) -> None:
    spec = get_command_spec("can-i")
    with pytest.raises(click.BadParameter):
        validate_output_format(fmt, spec)


def test_can_i_manifest_allows_table() -> None:
    spec = get_command_spec("can-i")
    assert validate_output_format("table", spec) == "table"
    assert validate_output_format("yaml", spec) == "yaml"


@pytest.mark.parametrize("fmt", ("wide", "name", "path", "raw"))
def test_can_i_cli_rejects_unsupported_output_flag(fmt: str) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["can-i", "-o", fmt, "namespace:read", "-n", "prod"])
    assert result.exit_code != 0
    assert "not a valid output format" in result.output
