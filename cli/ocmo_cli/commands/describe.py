"""ocmo describe — read or set an item's description.

Read: no --description flag → fetch and print description to stdout.
Write: --description flag → POST description to the API.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .._address import parse_address_or_exit
from .._client import OcmoCtx
from .._errors import sdk_command
from .._mutating import run_mutating
from .._options import namespace_option, yes_option
from .._output import as_dict

_DESCRIBE_HELP = """\
Read or set the Markdown description of a tree item.

Without --description, prints the current description. With --description, replaces it.

\b
Examples:
  ocmo -n prod describe app/web
  ocmo -n prod describe app/web --description "Production web config"
  ocmo -n prod describe app/web --description ./NOTES.md
  echo "My description" | ocmo -n prod describe app/web --description -
"""


def resolve_description_value(value: str) -> str:
    """Resolve --description to text from a literal, stdin, or file path."""
    if value == "-":
        return sys.stdin.read()
    if value.startswith("/") or value.startswith("."):
        return Path(value).read_text(encoding="utf-8")
    return value


@click.command("describe", help=_DESCRIBE_HELP)
@click.argument("address")
@click.option(
    "--description",
    "description_value",
    default=None,
    metavar="TEXT|-|PATH",
    help=("New description text, '-' for stdin, or a file path starting with '/' or '.'."),
)
@namespace_option()
@yes_option(help="Skip overwrite confirmation.")
@click.pass_obj
@sdk_command
def describe_cmd(
    ctx: OcmoCtx,
    address: str,
    description_value: str | None,
    namespace: str | None,
    yes: bool,
) -> None:
    """Read or set the description of a tree item.

    \b
    Read (no --description):
      ocmo -n prod describe app/web

    Write (--description):
      ocmo -n prod describe app/web --description "Notes for operators"
      ocmo -n prod describe app/web --description ./NOTES.md
      ocmo -n prod describe app/web --description -   # from stdin
    """
    path, _version = parse_address_or_exit(address)

    view = ctx.namespace_view(namespace)

    if description_value is not None:
        content = resolve_description_value(description_value)
        ns = ctx.require_namespace(namespace)

        from .._dry_run import format_describe_dry_run  # deferred

        def _action() -> None:
            view.describe_item(path=path, description=content)
            print(f"Description updated for {path!r}.")

        run_mutating(
            ctx,
            dry_run=False,
            yes=yes,
            plan_lines=[
                format_describe_dry_run(
                    path=path,
                    namespace=ns,
                    char_count=len(content),
                )
            ],
            confirm_message=f"Overwrite description for {path!r}?",
            action=_action,
            abort_exit_code=1,
            abort_via_err=True,
        )
    else:
        item = view.get_item(path=path)
        data = as_dict(item)
        description = data.get("description") or ""
        print(description, end="" if description.endswith("\n") else "\n")
