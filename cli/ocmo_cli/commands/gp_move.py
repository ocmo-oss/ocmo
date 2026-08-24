"""Hand-written ``ocmo move globalpermission`` command."""

from __future__ import annotations

import click

from .._address import parse_simple_address_or_exit
from .._client import OcmoCtx
from .._dry_run import format_generated_dry_run
from .._errors import sdk_command
from .._globalpermission_output import emit_get_globalpermission_output
from .._mutating import run_mutating
from .._options import dry_run_option, yes_option

_MOVE_GP_HELP = """\
Reorder a global permission rule.

\b
Examples:
  ocmo move globalpermission dev-read --position 1.5
  ocmo move globalpermission dev-read --position 2 --yes
"""


def _move_gp_confirm_message(rule_id: str, position: float) -> str:
    return f"Move global permission rule {rule_id!r} to position {position}. Continue?"


def _run_move_globalpermission(
    ctx: OcmoCtx,
    *,
    address: str,
    position: float,
    dry_run: bool,
    yes: bool,
) -> None:
    rule_id, _version = parse_simple_address_or_exit(address)
    sdk_kwargs = {"position": position}

    def _action() -> None:
        client = ctx.client()
        client.move_global_permission(rule_id, position=position)
        result = client.get_global_permission(rule_id)
        emit_get_globalpermission_output(result, ctx_fmt=ctx.output)

    run_mutating(
        ctx,
        dry_run=dry_run,
        yes=yes,
        plan_lines=format_generated_dry_run(
            op_id="move_global_permission",
            action="move",
            resource="globalpermission",
            path=rule_id,
            version=None,
            namespace=None,
            args=[],
            kwargs=sdk_kwargs,
            client_scope=True,
        ),
        confirm_message=_move_gp_confirm_message(rule_id, position),
        action=_action,
    )


@click.command("globalpermission", help=_MOVE_GP_HELP)
@click.argument("address")
@click.option(
    "--position",
    required=True,
    type=float,
    help="New sort position for the rule (fractional values allowed).",
)
@yes_option()
@dry_run_option()
@click.pass_obj
@sdk_command
def move_globalpermission_cmd(
    ctx: OcmoCtx,
    address: str,
    position: float,
    dry_run: bool,
    yes: bool,
) -> None:
    _run_move_globalpermission(
        ctx,
        address=address,
        position=position,
        dry_run=dry_run,
        yes=yes,
    )


def register_gp_move_command(root: click.Group) -> None:
    """Register hand-written ``move globalpermission`` on the generated move group."""
    from .._click_groups import attach_resource_command, ensure_resource_alias_group

    move_group = ensure_resource_alias_group(
        root,
        "move",
        help="Move items within the tree.",
    )
    attach_resource_command(
        move_group,
        move_globalpermission_cmd,
        canonical="globalpermission",
        aliases=["gp", "globalpermissions"],
    )
