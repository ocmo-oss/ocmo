"""Tests for ``ocmo describe``."""

from __future__ import annotations

import io

import pytest
from click.testing import CliRunner

from ocmo_cli.commands.describe import resolve_description_value
from ocmo_cli.main import cli
from tests.helpers import assert_help_excludes_io_flags


def test_resolve_description_value_literal() -> None:
    assert resolve_description_value("Production notes") == "Production notes"


def test_resolve_description_value_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("from stdin\n"))
    assert resolve_description_value("-") == "from stdin\n"


def test_resolve_description_value_relative_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    notes = tmp_path / "NOTES.md"
    notes.write_text("# Notes\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert resolve_description_value("./NOTES.md") == "# Notes\n"


def test_resolve_description_value_absolute_file(tmp_path) -> None:
    notes = tmp_path / "NOTES.md"
    notes.write_text("absolute path\n", encoding="utf-8")
    assert resolve_description_value(str(notes)) == "absolute path\n"


def test_describe_help_has_description_not_file() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["describe", "--help"])
    assert result.exit_code == 0, result.output
    assert "--description" in result.output
    assert_help_excludes_io_flags(result.output)


def test_describe_cli_rejects_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-n", "prod", "describe", "app/web", "-o", "json"])
    assert result.exit_code != 0
    assert "no such option" in result.output.lower() or "unknown option" in result.output.lower()
