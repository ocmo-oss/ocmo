"""Tests for ``ocmo resolve --mark-stable``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli.commands.resolve import resolve_cmd


def test_resolve_passes_mark_stable_to_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    view = MagicMock()
    result = MagicMock()
    result.__iter__ = lambda self: iter([])
    view.resolve.return_value = result

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.namespace_view.return_value = view
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = False

    monkeypatch.setattr(
        "ocmo_cli.commands.resolve.run_resolve_pipeline",
        lambda *_args, **_kwargs: None,
    )

    runner = CliRunner()
    result_cli = runner.invoke(
        resolve_cmd,
        ["app/web", "--mark-stable"],
        obj=ctx,
    )

    assert result_cli.exit_code == 0, result_cli.output
    view.resolve.assert_called_once_with("app/web", mark_stable=True)
