"""Tests for ``ocmo resolve`` group and subcommand help."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from ocmo_cli.main import cli

_RESOLVE_OPTIONS = (
    "--namespace",
    "--output",
    "--cast",
    "--param",
    "--cast-option",
    "--output-file",
    "--output-dir",
    "--rewrite",
    "--skip-existing",
    "--trace-only",
    "--property",
    "--version",
    "--exec-hooks",
    "--hook-timeout",
    "--trust-hooks",
    "--print-hooks",
    "--mark-stable",
)

_DRAFT_OPTIONS = (
    "--file",
    "--cast",
    "--param",
    "--cast-option",
    "--output-file",
    "--output-dir",
    "--trace-only",
    "--property",
    "--exec-hooks",
)


@pytest.mark.parametrize("flag", _RESOLVE_OPTIONS)
def test_resolve_group_help_lists_default_command_options(flag: str) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "--help"])
    assert result.exit_code == 0, result.output
    assert flag in result.output


def test_resolve_group_help_lists_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "--help"])
    assert result.exit_code == 0, result.output
    assert "draft" in result.output
    assert "parameters" in result.output


@pytest.mark.parametrize("flag", _DRAFT_OPTIONS)
def test_resolve_draft_help_lists_resolve_options(flag: str) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "draft", "--help"])
    assert result.exit_code == 0, result.output
    assert flag in result.output


def test_resolve_draft_help_has_no_version_or_field_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "draft", "--help"])
    assert result.exit_code == 0, result.output
    assert "--version" not in result.output
    assert "  -V," not in result.output
    assert "--field" not in result.output
    assert "--mark-stable" not in result.output
