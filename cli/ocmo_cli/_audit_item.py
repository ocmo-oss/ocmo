"""Shared helpers for audit commands that resolve a tree item."""

from __future__ import annotations

from typing import Any

from ._address import parse_simple_address_or_exit, reject_version
from ._client import OcmoCtx
from ._exit import USAGE_ERROR
from ._item_output import node_type_of
from ._output import err


def resolve_audit_item(
    ctx: OcmoCtx,
    address: str,
    namespace: str | None,
    *,
    command: str,
    allow_version_flag: bool = False,
) -> tuple[Any, str, str]:
    """Parse ADDRESS, resolve namespace view, and return (view, path, node_type)."""
    path, version = parse_simple_address_or_exit(address)
    reject_version(version, command=command, allow_flag=allow_version_flag)

    view = ctx.namespace_view(namespace)
    item = view.get_item(path=path)
    node_type = node_type_of(item)
    if not node_type:
        err(f"Could not determine item type for {path!r}.")
        raise SystemExit(USAGE_ERROR)

    return view, path, node_type
