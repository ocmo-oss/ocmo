"""Tests for resolve when the API returns zero output items."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ocmo_cli._exit import RESOLVE_EMPTY
from ocmo_cli.commands.resolve import run_resolve_pipeline


def test_run_resolve_pipeline_exits_when_no_items() -> None:
    result = MagicMock()
    result.__iter__ = lambda self: iter([])

    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True

    with pytest.raises(SystemExit) as exc:
        run_resolve_pipeline(
            ctx,
            result,
            path="app/web",
            ns="prod",
            output_fmt=None,
            output_file=None,
            output_dir=None,
            rewrite=False,
            skip_existing=False,
            trace_only=False,
            prop_path=None,
            exec_hooks=False,
            hook_timeout=60,
            trust_hooks_sha=None,
        )

    assert exc.value.code == RESOLVE_EMPTY
