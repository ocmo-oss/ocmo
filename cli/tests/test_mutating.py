"""Tests for shared mutating command flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ocmo_cli._mutating import run_mutating


def test_run_mutating_dry_run_short_circuits_without_confirm() -> None:
    ctx = MagicMock()
    ctx.dry_run = True
    ctx.yes = False
    action = MagicMock()

    with patch("ocmo_cli._dry_run.emit_dry_run_plan") as emit:
        run_mutating(
            ctx,
            dry_run=False,
            yes=False,
            plan_lines=["would mutate"],
            confirm_message="Continue?",
            action=action,
        )

    emit.assert_called_once_with("would mutate")
    action.assert_not_called()


def test_run_mutating_confirm_abort_uses_status() -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = False
    action = MagicMock()

    with (
        patch("ocmo_cli._mutating.confirm", return_value=False),
        patch("ocmo_cli._mutating.status") as status,
        pytest.raises(SystemExit) as exc,
    ):
        run_mutating(
            ctx,
            dry_run=False,
            yes=False,
            plan_lines=None,
            confirm_message="Continue?",
            action=action,
        )

    assert exc.value.code == 0
    status.assert_called_once_with("Aborted.")
    action.assert_not_called()


def test_run_mutating_ctx_yes_bypasses_confirm() -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = True
    action = MagicMock()

    with patch("ocmo_cli._mutating.confirm") as confirm:
        run_mutating(
            ctx,
            dry_run=False,
            yes=False,
            plan_lines=None,
            confirm_message="Continue?",
            action=action,
        )

    confirm.assert_not_called()
    action.assert_called_once()


def test_run_mutating_abort_via_err() -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = False
    action = MagicMock()

    with (
        patch("ocmo_cli._mutating.confirm", return_value=False),
        patch("ocmo_cli._mutating.err") as err,
        pytest.raises(SystemExit) as exc,
    ):
        run_mutating(
            ctx,
            dry_run=False,
            yes=False,
            plan_lines=None,
            confirm_message="Continue?",
            action=action,
            abort_exit_code=1,
            abort_via_err=True,
        )

    assert exc.value.code == 1
    err.assert_called_once_with("Aborted.")
    action.assert_not_called()
