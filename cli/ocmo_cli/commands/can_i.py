"""ocmo can-i — check permissions."""

from __future__ import annotations

import sys

import click

from .._client import OcmoCtx
from .._errors import sdk_command
from .._options import can_i_output_option, namespace_option
from .._output import as_dict
from .._output_manifest import emit_command_output


@click.command(
    "can-i",
    help="Check whether the current principal may perform one or more operations.",
)
@click.argument("operations", nargs=-1, required=True, metavar="OPERATION...")
@namespace_option()
@can_i_output_option()
@click.option("--resource", default=None, help="Tree path for in-namespace permission probes.")
@click.pass_obj
@sdk_command
def can_i_cmd(
    ctx: OcmoCtx,
    operations: tuple[str, ...],
    namespace: str | None,
    output_fmt: str | None,
    resource: str | None,
) -> None:
    """Examples:

    ocmo can-i config:read config:write -n prod
    ocmo can-i secret:read --namespace prod --resource app/db
    """
    ns = namespace or ctx.namespace
    result = ctx.client().can_i(
        operations=list(operations),
        namespace=ns,
        resource=resource,
    )
    data = as_dict(result)
    emit_command_output("can-i", data, output_fmt, ctx_fmt=ctx.output)
    allowed = data.get("allowed")
    if isinstance(allowed, dict):
        if not all(allowed.values()):
            sys.exit(4)
    elif not allowed:
        sys.exit(4)
