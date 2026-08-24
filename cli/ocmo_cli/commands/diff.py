"""ocmo diff — coloured unified diff between two versions or two items."""

from __future__ import annotations

import sys

import click

from .._address import AddressError
from .._client import OcmoCtx
from .._diff_input import diff_sdk_kwargs, parse_diff_spec, render_diff_response
from .._errors import sdk_command
from .._exit import USAGE_ERROR
from .._options import namespace_option, tree_version_option


@click.command("diff")
@click.argument("addresses", nargs=-1, required=True)
@tree_version_option()
@click.option("--from-version", default=None, metavar="VER", help="Left-side version or tag.")
@click.option("--to-version", default=None, metavar="VER", help="Right-side version or tag.")
@click.option(
    "--reveal",
    is_flag=True,
    default=False,
    help="Decrypt secret values for diff (requires secret:read).",
)
@namespace_option()
@click.pass_obj
@sdk_command
def diff_cmd(
    ctx: OcmoCtx,
    addresses: tuple[str, ...],
    version_flag: str | None,
    from_version: str | None,
    to_version: str | None,
    reveal: bool,
    namespace: str | None,
) -> None:
    """Show a unified diff between two versions or two items.

    \b
    Examples:
      ocmo -n prod diff app/web
      ocmo -n prod diff app/web@2..13
      ocmo -n prod diff app/web --from-version 3 --to-version 5
      ocmo -n prod diff app/web@2 app/staging/web@14
    """
    try:
        spec = parse_diff_spec(
            addresses,
            version_flag=version_flag,
            from_version=from_version,
            to_version=to_version,
        )
    except AddressError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(USAGE_ERROR)

    path, kwargs = diff_sdk_kwargs(spec, reveal=reveal)
    result = ctx.namespace_view(namespace).diff_item(path=path, **kwargs)

    if getattr(result, "decryption_required", False):
        print(
            "Error: secret diff requires --reveal to compare decrypted values.",
            file=sys.stderr,
        )
        raise SystemExit(USAGE_ERROR)

    diff_text = render_diff_response(result)
    if sys.stdout.isatty():
        _print_coloured_diff(diff_text)
    else:
        print(diff_text, end="" if diff_text.endswith("\n") else "\n")


def _print_coloured_diff(text: str) -> None:
    try:
        from rich.console import Console
        from rich.syntax import Syntax

        console = Console()
        syntax = Syntax(text, "diff", theme="monokai", line_numbers=False)
        console.print(syntax)
    except ImportError:
        print(text, end="" if text.endswith("\n") else "\n")
