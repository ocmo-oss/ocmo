"""Hand-written ``ocmo move item`` and ``ocmo copy item`` commands."""

from __future__ import annotations

from typing import Any

import click

from .._address import (
    parse_address_or_exit,
    parse_simple_address_or_exit,
    resolve_relocate_target,
)
from .._click_groups import attach_resource_command, ensure_resource_alias_group
from .._client import OcmoCtx
from .._dry_run import format_generated_dry_run
from .._errors import sdk_command
from .._exit import USAGE_ERROR
from .._mutating import run_mutating
from .._options import dry_run_option, namespace_option, yes_option
from .._output import err, status

_MOVE_ITEM_HELP = """\
Move a tree item or folder subtree to a new path.

TARGET uses Unix-style semantics: a trailing ``/`` places the source inside that
directory (keeping its leaf name); otherwise TARGET is the exact destination path.

\b
Examples:
  ocmo -n prod move item app/web app/archive/web
  ocmo -n prod move item b/c/d a/
"""

_COPY_ITEM_HELP = """\
Copy a tree item or folder subtree to a new path.

When SOURCE includes ``@tag`` or ``@version``, that version is copied; otherwise
the API default tag (``latest``) is used.

TARGET uses Unix-style semantics: a trailing ``/`` places the source inside that
directory (keeping its leaf name); otherwise TARGET is the exact destination path.

\b
Examples:
  ocmo -n prod copy item app/web app/staging/web
  ocmo -n prod copy item app/web@stable app/staging/
  ocmo -n prod copy item b/c/d a/
"""


def _parse_source_target(
    source: str,
    target: str,
    *,
    allow_source_version: bool,
) -> tuple[str, str | None, str]:
    source_path, source_version = parse_address_or_exit(source)
    target_path, target_version = parse_simple_address_or_exit(target)
    if target_version:
        err("TARGET does not support @version.")
        raise SystemExit(USAGE_ERROR)

    if source_version and not allow_source_version:
        err("SOURCE does not support @version or @tag for move.")
        raise SystemExit(USAGE_ERROR)

    return source_path, source_version, target_path


def _relocate_confirm_message(action: str, source_path: str, destination_path: str) -> str:
    return f"{action.capitalize()} item {source_path!r} to {destination_path!r}. Continue?"


def _relocate_success_message(action: str, source_path: str, destination_path: str) -> str:
    past = "moved" if action == "move" else "copied"
    return f"Item {source_path!r} was {past} to {destination_path!r}."


def _run_item_relocate(
    ctx: OcmoCtx,
    *,
    op_id: str,
    action: str,
    source: str,
    target: str,
    namespace: str | None,
    dry_run: bool,
    yes: bool,
    allow_source_version: bool,
) -> None:
    source_path, source_version, target_path = _parse_source_target(
        source,
        target,
        allow_source_version=allow_source_version,
    )
    destination_path = resolve_relocate_target(source_path, target_path)

    sdk_kwargs: dict[str, Any] = {"target_path": destination_path}
    if op_id == "copy_item" and source_version:
        sdk_kwargs["tag_to_copy"] = source_version

    ns = ctx.require_namespace(namespace)

    def _action() -> None:
        view = ctx.namespace_view(namespace)
        if op_id == "move_item":
            view.move_item(source_path, **sdk_kwargs)
        else:
            view.copy_item(source_path, **sdk_kwargs)
        status(_relocate_success_message(action, source_path, destination_path))

    run_mutating(
        ctx,
        dry_run=dry_run,
        yes=yes,
        plan_lines=format_generated_dry_run(
            op_id=op_id,
            action=action,
            resource="item",
            path=source_path,
            version=source_version if op_id == "copy_item" else None,
            namespace=ns,
            args=[],
            kwargs=sdk_kwargs,
            client_scope=False,
        ),
        confirm_message=_relocate_confirm_message(action, source_path, destination_path),
        action=_action,
    )


def _build_relocate_command(action: str) -> click.Command:
    help_text = _MOVE_ITEM_HELP if action == "move" else _COPY_ITEM_HELP
    op_id = "move_item" if action == "move" else "copy_item"
    allow_source_version = action == "copy"

    @click.command("item", help=help_text)
    @click.argument("source")
    @click.argument("target")
    @namespace_option()
    @yes_option()
    @dry_run_option()
    @click.pass_obj
    @sdk_command
    def relocate_cmd(
        ctx: OcmoCtx,
        source: str,
        target: str,
        namespace: str | None,
        dry_run: bool,
        yes: bool,
    ) -> None:
        _run_item_relocate(
            ctx,
            op_id=op_id,
            action=action,
            source=source,
            target=target,
            namespace=namespace,
            dry_run=dry_run,
            yes=yes,
            allow_source_version=allow_source_version,
        )

    return relocate_cmd


move_item_cmd = _build_relocate_command("move")
copy_item_cmd = _build_relocate_command("copy")


def register_item_relocate_commands(root: click.Group) -> None:
    """Register hand-written ``move item`` / ``copy item`` commands."""
    move_group = ensure_resource_alias_group(
        root,
        "move",
        help="Move items within the tree.",
    )
    attach_resource_command(move_group, move_item_cmd, canonical="item", aliases=[])

    copy_group = ensure_resource_alias_group(
        root,
        "copy",
        help="Copy items within the tree.",
    )
    attach_resource_command(copy_group, copy_item_cmd, canonical="item", aliases=[])
