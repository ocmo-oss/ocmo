"""Factory for thin client-scoped commands (whoami, api-health, etc.)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import click

from ._client import OcmoCtx
from ._errors import sdk_command
from ._options import output_option
from ._output import as_dict
from ._output_manifest import emit_command_output


def client_command(
    name: str,
    *,
    help: str,
    manifest_key: str,
    method: str,
) -> click.Command:
    """Build a command that calls a client method and emits manifest output."""

    @click.command(name, help=help)
    @output_option(manifest_key)
    @click.pass_obj
    @sdk_command
    def cmd(ctx: OcmoCtx, output_fmt: str | None) -> None:
        fetch: Callable[[], Any] = getattr(ctx.client(), method)
        data = as_dict(fetch())
        emit_command_output(manifest_key, data, output_fmt, ctx_fmt=ctx.output)

    return cmd
