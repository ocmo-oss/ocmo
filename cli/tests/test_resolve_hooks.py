"""Tests for resolve hook printing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from ocmo.resolve import ResolverConfig

from ocmo_cli.commands.resolve import _exec_hook, _extract_hooks, _print_hooks


def test_extract_hooks_from_resolver_config():
    result = SimpleNamespace(
        resolver=ResolverConfig(
            {
                "hooks": {
                    "validate": "ls -la {!conf}",
                    "post_resolve": "ls -la",
                },
            }
        ),
    )
    hooks = _extract_hooks(result)
    assert hooks is not None
    assert hooks.validate == "ls -la {!conf}"
    assert hooks.post_resolve == "ls -la"


def test_print_hooks_writes_commands(capsys: pytest.CaptureFixture[str]) -> None:
    result = SimpleNamespace(
        resolver=ResolverConfig(
            {
                "hooks": {
                    "validate": "ls -la {!conf}",
                    "post_resolve": "ls -la",
                },
            }
        ),
    )
    _print_hooks(result)
    captured = capsys.readouterr()
    assert "validate: ls -la {!conf}" in captured.err
    assert "post_resolve: ls -la" in captured.err
    assert captured.out == ""


def test_print_hooks_without_resolver_reports_none(capsys: pytest.CaptureFixture[str]) -> None:
    _print_hooks(SimpleNamespace(resolver=None))
    captured = capsys.readouterr()
    assert captured.err == "No hooks configured.\n"
    assert captured.out == ""


def test_exec_hook_streams_subprocess_output_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    proc = MagicMock()
    proc.communicate.return_value = ("line-one\nline-two\n", "")
    proc.returncode = 0

    with patch("ocmo_cli.commands.resolve.subprocess.Popen", return_value=proc):
        _exec_hook("echo test", env={"PATH": "/usr/bin"}, timeout=60, cwd=".")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "[hook] line-one",
        "[hook] line-two",
    ]
