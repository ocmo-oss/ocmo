"""Shared dry-run and confirmation flow for mutating CLI commands."""

from __future__ import annotations

from collections.abc import Callable

from ._client import OcmoCtx
from ._output import confirm, err, status


def run_mutating(
    ctx: OcmoCtx,
    *,
    dry_run: bool,
    yes: bool,
    plan_lines: list[str] | None,
    confirm_message: str | None,
    action: Callable[[], None],
    abort_exit_code: int = 0,
    abort_via_err: bool = False,
) -> None:
    """Run a mutating action with optional dry-run plan and confirmation."""
    if ctx.dry_run or dry_run:
        if plan_lines:
            from ._dry_run import emit_dry_run_plan  # deferred

            for line in plan_lines:
                emit_dry_run_plan(line)
        return

    if confirm_message and not (yes or ctx.yes):
        if not confirm(confirm_message, yes=False):
            if abort_via_err:
                err("Aborted.")
            else:
                status("Aborted.")
            raise SystemExit(abort_exit_code)

    action()
