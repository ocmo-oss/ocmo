"""Shared lazy-delegation helpers for startup-safe Click stubs."""

from __future__ import annotations

from typing import Any

import click


class ClickLazyMixin:
    """Delegate common Click entry points to a lazily loaded target."""

    def _lazy_target(self) -> click.Command | click.Group:
        raise NotImplementedError

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: click.Context | None = None,
        **extra: Any,
    ) -> click.Context:
        return self._lazy_target().make_context(info_name, args, parent=parent, **extra)

    def invoke(self, ctx: click.Context) -> Any:
        return self._lazy_target().invoke(ctx)

    def shell_complete(self, ctx: click.Context, incomplete: str) -> list[click.shell_completion.CompletionItem]:
        return self._lazy_target().shell_complete(ctx, incomplete)
