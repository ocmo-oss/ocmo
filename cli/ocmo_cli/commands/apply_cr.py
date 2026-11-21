"""Apply (merge) a change request into a new published version."""

from __future__ import annotations

import click

from ocmo_cli._client import OcmoCtx
from ocmo_cli._errors import sdk_command
from ocmo_cli._options import namespace_option


@click.command("apply-cr")
@click.argument("path")
@click.option("--number", "-n", type=int, default=None, help="Change request number (if omitted, parse from path@~N)")
@namespace_option()
@click.pass_obj
@sdk_command
def apply_cr_cmd(ctx: OcmoCtx, path: str, number: int | None, namespace: str | None) -> None:
    """Apply an open change request, creating a new config/template/secret version."""
    ref_path = path
    cr_number = number
    if "@~" in path:
        base, suffix = path.rsplit("@", 1)
        if suffix.startswith("~") and suffix[1:].isdigit():
            ref_path = base
            cr_number = int(suffix[1:])
    if cr_number is None:
        raise click.UsageError("Provide --number or use path@~N (e.g. app/web@~1)")
    ns = ctx.ns(namespace)
    ns.apply_change_request(ref_path.strip("/"), number=cr_number)
    click.echo(f"Applied change request ~{cr_number} on {ref_path}")
