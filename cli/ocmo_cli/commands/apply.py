"""ocmo apply — upload a local file as a named OCMO item.

Replaces the manifest-based approach with a direct file-to-tree-path mapping:

  ocmo -n prod apply -f nginx.conf app/nginx/site -t template
  ocmo -n prod apply -f config.yaml app/web/main        # -t inferred as config
  ocmo -n prod apply -f - app/web/inline -t config      # read from stdin

The type is inferred from the file extension when -t is omitted:
  *.yaml / *.yml / *.json → config
  everything else          → template
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import click

from .._address import parse_address_or_exit
from .._client import OcmoCtx
from .._config_content import prepare_config_apply_content
from .._errors import sdk_command
from .._exit import USAGE_ERROR
from .._options import dry_run_option, namespace_option
from .._output import err, status
from .._resolver_output import print_resolver_token

if TYPE_CHECKING:
    from ocmo import NamespaceView

_VALID_TYPES = ("config", "template", "secret", "resolver")
_VALID_TYPES_DISPLAY = " | ".join(_VALID_TYPES)

_HELP = """\
Create or update a tree item from a local file.

When -t is omitted, type is inferred from the file extension:
*.yaml / *.yml / *.json become config; all other extensions become template.

\b
Examples:
  ocmo -n prod apply -f config.yaml app/web/main
  ocmo -n prod apply -f nginx.conf app/nginx/site -t template
  cat resolver.yaml | ocmo -n prod apply -f - app/resolvers/default -t resolver
"""


@click.command("apply", help=_HELP)
@click.argument("tree_path")
@click.option(
    "-f",
    "--file",
    "file_path",
    required=True,
    metavar="FILE|-",
    help="Source file to upload. Use '-' to read from stdin.",
)
@click.option(
    "-t",
    "--type",
    "item_type",
    type=click.Choice(list(_VALID_TYPES)),
    default=None,
    help=f"Item type: {_VALID_TYPES_DISPLAY}. Inferred from extension when omitted.",
)
@namespace_option()
@dry_run_option(help="Print plan without uploading.")
@click.pass_obj
@sdk_command
def apply_cmd(
    ctx: OcmoCtx,
    tree_path: str,
    file_path: str,
    item_type: str | None,
    namespace: str | None,
    dry_run: bool,
) -> None:
    path, _version = parse_address_or_exit(tree_path)

    # Read content
    if file_path == "-":
        content = sys.stdin.read()
        source_name = "<stdin>"
    else:
        with open(file_path) as f:
            content = f.read()
        source_name = file_path

    # Infer type from extension when not given
    kind = item_type or _infer_type(file_path)
    if kind == "config":
        content = prepare_config_apply_content(content, source_name=source_name)

    if dry_run or ctx.dry_run:
        from .._dry_run import emit_dry_run_plan, format_apply_dry_run  # deferred

        ns = namespace or ctx.namespace
        emit_dry_run_plan(
            format_apply_dry_run(
                kind=kind,
                path=path,
                source_name=source_name,
                namespace=ns if isinstance(ns, str) else None,
            )
        )
        return

    view = ctx.namespace_view(namespace)

    created, result = _upload(view, path, content, kind)
    verb = "Created" if created else "Updated"
    status(f"{verb} {kind} {path!r}.")
    if kind == "resolver" and created:
        print_resolver_token(result)


def _infer_type(file_path: str) -> str:
    if file_path == "-":
        return "config"
    import os

    ext = os.path.splitext(file_path)[1].lower()
    return "config" if ext in (".yaml", ".yml", ".json") else "template"


def _upload(view: NamespaceView, path: str, content: str, kind: str) -> tuple[bool, Any]:
    """Upload content; returns (created, api_result)."""
    _update, _create = _get_methods(view, kind)
    try:
        result = _update(path=path, content=content)
        return False, result
    except Exception:
        result = _create(path=path, content=content)
        return True, result


def _get_methods(
    view: NamespaceView,
    kind: str,
) -> tuple[Callable[..., Any], Callable[..., Any]]:
    methods = {
        "config": (view.update_config, view.create_config),
        "template": (view.update_template, view.create_template),
        "secret": (view.update_secret, view.create_secret),
        "resolver": (view.update_resolver, view.create_resolver),
    }
    if kind not in methods:
        err(f"Unknown type {kind!r}. Valid: {_VALID_TYPES_DISPLAY}")
        raise SystemExit(USAGE_ERROR)
    return methods[kind]
