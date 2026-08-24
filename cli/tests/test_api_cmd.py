"""Tests for hidden ``ocmo api`` escape hatch."""

from __future__ import annotations

import click
from click.testing import CliRunner

from ocmo_cli.main import cli


def test_api_hidden_from_root_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output
    assert "  api-health" in result.output
    assert "\n  api " not in result.output
    assert "\n  api\n" not in result.output


def test_api_still_accessible_directly() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["api", "--help"])
    assert result.exit_code == 0, result.output
    assert "operation_id" in result.output


def test_api_hidden_from_click_completion_candidates() -> None:
    from click.core import _complete_visible_commands

    ctx = click.Context(cli)
    completions = [name for name, _ in _complete_visible_commands(ctx, "")]
    assert "api-health" in completions
    assert "api" not in completions
