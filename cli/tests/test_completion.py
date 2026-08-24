"""Tests for ``ocmo completion``."""

from __future__ import annotations

import os

import pytest
from click.shell_completion import get_completion_class
from click.testing import CliRunner

from ocmo_cli.commands.completion import completion_cmd
from ocmo_cli.main import cli


def _bash_completions(words: list[str]) -> list[str]:
    comp_cls = get_completion_class("bash")
    assert comp_cls is not None
    comp = comp_cls(cli, ctx_args={}, prog_name="ocmo", complete_var="_OCMO_COMPLETE")
    os.environ["COMP_WORDS"] = " ".join(words)
    os.environ["COMP_CWORD"] = str(len(words) - 1)
    args, incomplete = comp.get_completion_args()
    return [item.value for item in comp.get_completions(args, incomplete)]


def test_completion_bash_emits_script() -> None:
    runner = CliRunner()
    result = runner.invoke(completion_cmd, ["bash"])
    assert result.exit_code == 0, result.output
    assert "_ocmo_completion" in result.output
    assert "bash_complete" in result.output


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_emits_script_for_supported_shells(shell: str) -> None:
    runner = CliRunner()
    result = runner.invoke(completion_cmd, [shell])
    assert result.exit_code == 0, result.output
    assert "complete" in result.output.lower()


def test_completion_lists_top_level_commands() -> None:
    completions = _bash_completions(["ocmo", ""])
    assert "import" in completions
    assert "export" in completions
    assert "resolve" in completions
    assert "get" in completions
    assert "api" not in completions


def test_completion_lists_auth_subcommands() -> None:
    completions = _bash_completions(["ocmo", "auth", ""])
    assert "login" in completions
    assert "logout" in completions
    assert "status" in completions


def test_completion_lists_resolve_subcommands() -> None:
    completions = _bash_completions(["ocmo", "resolve", ""])
    assert "draft" in completions
    assert "parameters" in completions


def test_completion_lists_resolve_default_command_flags() -> None:
    completions = _bash_completions(["ocmo", "resolve", "--"])
    assert "--cast" in completions
    assert "--output-dir" in completions
    assert "--trace-only" in completions


def test_completion_lists_import_flags() -> None:
    completions = _bash_completions(["ocmo", "import", "--"])
    assert "--from-metadata" in completions
    assert "--type-override" in completions
    assert "--verify" in completions


def test_completion_lists_get_item_flags() -> None:
    completions = _bash_completions(["ocmo", "get", "item", "--"])
    assert "--version" in completions
    assert "--namespace" in completions


def test_completion_lists_global_flags() -> None:
    completions = _bash_completions(["ocmo", "--"])
    assert "--namespace" in completions
    assert "--dry-run" in completions
    assert "--yes" in completions
