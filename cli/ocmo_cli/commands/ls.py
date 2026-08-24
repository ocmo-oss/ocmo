"""ocmo ls / ocmo tree — list or render the item tree under a path."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import click

from .._address import parse_address_or_exit
from .._client import OcmoCtx
from .._errors import sdk_command
from .._exit import USAGE_ERROR
from .._ls_wide import (
    LS_WIDE_SORT_CHOICES,
    basic_ls_row,
    enrich_ls_rows,
    sort_wide_rows,
)
from .._options import namespace_option, output_option
from .._output import as_dict, emit, emit_table, err
from .._output_manifest import columns_for_format, get_command_spec, resolve_effective_format

if TYPE_CHECKING:
    from ocmo import NamespaceView, OcmoClient

_LS_HELP = """\
List the direct children of a tree path, or the namespace root when ADDRESS is omitted.

\b
Examples:
  ocmo -n prod ls
  ocmo -n prod ls app/
  ocmo -n prod ls app/ -R
  ocmo -n prod ls app/ --hide-folders
  ocmo -n prod ls --hide-system
  ocmo -n prod ls -o json
  ocmo -n prod ls -o wide
  ocmo -n prod ls -o wide --sort updated
  ocmo -n prod ls -o wide --sort created
  ocmo -n prod ls -o name
  ocmo -n prod ls -o path
"""

_TREE_HELP = """\
Render the subtree under a path in tree format.

\b
Examples:
  ocmo -n prod tree
  ocmo -n prod tree app/
  ocmo -n prod tree --depth 2
  ocmo -n prod tree --hide-system
  ocmo -n prod tree --emoji
"""

_TREE_TYPE_EMOJI: dict[str, str] = {
    "folder": "📁",
    "config": "📄",
    "template": "📜",
    "secret": "🔒",
    "resolver": "⚡",
}


def _navigate(
    view: NamespaceView,
    address: str,
    *,
    recursive: bool,
    limit: int | None,
) -> tuple[str, dict[str, Any]]:
    kwargs: dict[str, Any] = {}
    if recursive:
        kwargs["recursive"] = True
    if limit is not None:
        kwargs["limit"] = limit

    if address:
        path, _version = parse_address_or_exit(address)
        result = view.navigate_path(path=path, **kwargs)
    else:
        path = ""
        result = view.navigate_root(**kwargs)

    data = as_dict(result)
    return path, data


@click.command("ls", help=_LS_HELP)
@click.argument("address", default="", required=False)
@namespace_option()
@output_option("ls")
@click.option(
    "-R",
    "--recursive",
    is_flag=True,
    default=False,
    help="Fetch the full subtree (not just direct children).",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Maximum number of items to return.",
)
@click.option(
    "--hide-folders",
    is_flag=True,
    default=False,
    help="Omit folder nodes from the listing.",
)
@click.option(
    "--hide-system",
    is_flag=True,
    default=False,
    help="Omit built-in namespace items (_permissions, _webhooks, …).",
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(LS_WIDE_SORT_CHOICES, case_sensitive=False),
    default=None,
    help="Sort wide output by path, type, created, or update time (requires -o wide).",
)
@click.pass_obj
@sdk_command
def ls_cmd(
    ctx: OcmoCtx,
    address: str,
    namespace: str | None,
    output_fmt: str | None,
    recursive: bool,
    limit: int | None,
    hide_folders: bool,
    hide_system: bool,
    sort_by: str | None,
) -> None:
    view = ctx.namespace_view(namespace)
    client = ctx.client()
    fmt = resolve_effective_format(output_fmt, ctx.output, get_command_spec("ls"))
    _validate_ls_sort(sort_by, fmt)

    path, data = _navigate(view, address, recursive=recursive, limit=limit)
    system_paths = _load_system_paths(client) if hide_system else frozenset()
    rows = _filter_navigation_rows(
        _navigation_rows(data),
        hide_folders=hide_folders,
        hide_system=hide_system,
        system_paths=system_paths,
    )

    if fmt == "wide":
        _render_wide_table(
            client,
            view,
            ctx.require_namespace(namespace),
            rows,
            sort_by=sort_by or "path",
            command_name="ls",
        )
    elif fmt == "table":
        _render_table(rows, command_name="ls")
    elif fmt in ("name", "path"):
        emit(rows, fmt)
    elif fmt == "json":
        import json as _json

        payload = _filter_navigate_data(
            data,
            hide_folders=hide_folders,
            hide_system=hide_system,
            system_paths=system_paths,
        )
        print(_json.dumps(payload, default=str, indent=2))
    elif fmt == "yaml" or (fmt and fmt.startswith("jsonpath=")):
        emit(
            _filter_navigate_data(
                data,
                hide_folders=hide_folders,
                hide_system=hide_system,
                system_paths=system_paths,
            ),
            fmt,
        )
    else:
        err(f"Unsupported output format for ocmo ls: {fmt!r}")
        raise SystemExit(USAGE_ERROR)


@click.command("tree", help=_TREE_HELP)
@click.argument("address", default="", required=False)
@namespace_option()
@click.option(
    "--depth",
    default=None,
    type=click.IntRange(1),
    help="Maximum nesting depth to display (default: unlimited).",
)
@click.option(
    "--hide-system",
    is_flag=True,
    default=False,
    help="Omit built-in namespace items (_permissions, _webhooks, …).",
)
@click.option(
    "--emoji",
    is_flag=True,
    default=False,
    help="Show item-type emojis before names instead of [type] suffixes.",
)
@click.pass_obj
@sdk_command
def tree_cmd(
    ctx: OcmoCtx,
    address: str,
    namespace: str | None,
    depth: int | None,
    hide_system: bool,
    emoji: bool,
) -> None:
    if ctx.output is not None:
        err("ocmo tree does not support -o/--output; output is always a tree view.")
        raise SystemExit(USAGE_ERROR)

    view = ctx.namespace_view(namespace)
    client = ctx.client()

    path, data = _navigate(view, address, recursive=True, limit=None)
    system_paths = _load_system_paths(client) if hide_system else frozenset()
    rows = _filter_navigation_rows(
        _navigation_rows(data),
        hide_folders=False,
        hide_system=hide_system,
        system_paths=system_paths,
    )

    tree_rows = _build_tree_hierarchy(
        rows,
        root_prefix=path.strip("/") if address else "",
    )
    _render_plain_tree(tree_rows, prefix="", connector="", max_depth=depth, use_emoji=emoji)


def _validate_ls_sort(sort_by: str | None, fmt: str | None) -> None:
    if sort_by is not None and fmt != "wide":
        err("--sort is only supported with -o wide.")
        raise SystemExit(USAGE_ERROR)


_DEFAULT_BUILTIN_NAMESPACE_PATHS = frozenset(
    {
        "_permissions",
        "_permissions.schema",
        "_webhooks",
        "_webhooks.schema",
        "_webhooks_secret",
        "_git_sync",
        "_git_sync.schema",
        "_git_sync_secret",
    }
)


def _load_system_paths(client: OcmoClient) -> frozenset[str]:
    """Return built-in namespace tree paths from ``/api/version`` when available."""
    version_info = None
    if hasattr(client, "version_info"):
        try:
            version_info = client.version_info()
        except Exception:
            version_info = None
    if not version_info:
        return _DEFAULT_BUILTIN_NAMESPACE_PATHS

    payload = version_info.get("builtin_namespace_paths") if isinstance(version_info, dict) else None
    if not isinstance(payload, dict):
        return _DEFAULT_BUILTIN_NAMESPACE_PATHS

    order = payload.get("order")
    if isinstance(order, list) and order:
        return frozenset(str(path).strip("/") for path in order if str(path).strip("/"))

    paths: set[str] = set()
    for section in ("config", "secret", "schema"):
        values = payload.get(section)
        if isinstance(values, list):
            paths.update(str(path).strip("/") for path in values if str(path).strip("/"))
    return frozenset(paths) if paths else _DEFAULT_BUILTIN_NAMESPACE_PATHS


def _node_path(node: Any) -> str:
    item = node if isinstance(node, dict) else vars(node)
    return str(item.get("path") or "").strip("/")


def _node_type(node: Any) -> str:
    item = node if isinstance(node, dict) else vars(node)
    return item.get("node_type") or ""


def _filter_navigation_rows(
    rows: Sequence[Any],
    *,
    hide_folders: bool,
    hide_system: bool,
    system_paths: frozenset[str],
) -> list[Any]:
    if not hide_folders and not hide_system:
        return list(rows)
    filtered: list[Any] = []
    for node in rows:
        if hide_folders and _node_type(node) == "folder":
            continue
        if hide_system and _node_path(node) in system_paths:
            continue
        item = node if isinstance(node, dict) else dict(vars(node))
        children = item.get("children") or []
        if children:
            item = {
                **item,
                "children": _filter_navigation_rows(
                    children,
                    hide_folders=hide_folders,
                    hide_system=hide_system,
                    system_paths=system_paths,
                ),
            }
        filtered.append(item)
    return filtered


def _filter_navigate_data(
    data: dict[str, Any],
    *,
    hide_folders: bool,
    hide_system: bool,
    system_paths: frozenset[str],
) -> dict[str, Any]:
    if not hide_folders and not hide_system:
        return data
    payload = dict(data)
    payload["children"] = _filter_navigation_rows(
        payload.get("children") or [],
        hide_folders=hide_folders,
        hide_system=hide_system,
        system_paths=system_paths,
    )
    item = payload.get("item")
    if payload.get("is_leaf") and item:
        if hide_folders and _node_type(item) == "folder":
            payload["item"] = None
        elif hide_system and _node_path(item) in system_paths:
            payload["item"] = None
    if payload.get("children"):
        payload["children_count"] = len(payload["children"])
    elif (hide_folders or hide_system) and not payload.get("is_leaf"):
        payload["children_count"] = 0
    return payload


def _navigation_rows(data: dict[str, Any]) -> list[Any]:
    """Return the nodes to list for a navigate response.

    Folder paths expose direct children; leaf paths expose the matched item itself.
    """
    children = data.get("children") or []
    if children:
        return children
    item = data.get("item")
    if data.get("is_leaf") and item:
        return [item]
    return []


def _build_tree_hierarchy(nodes: Sequence[Any], *, root_prefix: str = "") -> list[dict[str, Any]]:
    """Nest flat navigate rows (recursive API) into a path hierarchy."""
    root_prefix = root_prefix.strip("/")

    prepared: list[dict[str, Any]] = []
    for raw in nodes:
        item = raw if isinstance(raw, dict) else dict(vars(raw))
        path = (item.get("path") or "").strip("/")
        if not path or (root_prefix and path == root_prefix):
            continue
        prepared.append({**item, "children": []})

    if not prepared:
        return []

    by_path = {node["path"]: node for node in prepared}
    roots: list[dict[str, Any]] = []

    for node in sorted(prepared, key=lambda item: item["path"]):
        path = node["path"]
        parent_path = path.rsplit("/", 1)[0] if "/" in path else None

        if parent_path and parent_path in by_path:
            by_path[parent_path]["children"].append(node)
            continue

        if root_prefix:
            if parent_path == root_prefix:
                roots.append(node)
            else:
                roots.append(node)
        elif parent_path is None:
            roots.append(node)
        else:
            roots.append(node)

    def _sort_children(items: list[dict[str, Any]]) -> None:
        items.sort(key=lambda item: item.get("path") or "")
        for item in items:
            if item["children"]:
                _sort_children(item["children"])

    _sort_children(roots)
    return roots


def _tree_node_label(node: dict[str, Any], *, use_emoji: bool) -> str:
    node_name = node.get("name") or node.get("path") or str(node)
    node_type = node.get("node_type") or ""
    if use_emoji:
        icon = _TREE_TYPE_EMOJI.get(node_type, "")
        return f"{icon} {node_name}" if icon else node_name
    type_str = f"  [{node_type}]" if node_type else ""
    return f"{node_name}{type_str}"


def _render_plain_tree(
    children: Sequence[Any],
    prefix: str,
    connector: str = "",
    *,
    max_depth: int | None = None,
    current_depth: int = 1,
    use_emoji: bool = False,
) -> None:
    for i, item in enumerate(children):
        is_last = i == len(children) - 1
        branch = "└── " if is_last else "├── "
        node = item if isinstance(item, dict) else vars(item)
        print(f"{prefix}{connector}{branch}{_tree_node_label(node, use_emoji=use_emoji)}")
        sub = node.get("children") or []
        if sub and (max_depth is None or current_depth < max_depth):
            child_prefix = prefix + connector + ("    " if is_last else "│   ")
            _render_plain_tree(
                sub,
                prefix=child_prefix,
                max_depth=max_depth,
                current_depth=current_depth + 1,
                use_emoji=use_emoji,
            )


def _render_table(children: Sequence[Any], *, command_name: str) -> None:
    rows = []
    for item in children:
        node = item if isinstance(item, dict) else vars(item)
        rows.append(basic_ls_row(node))
    rows.sort(key=lambda row: row["path"])
    spec = get_command_spec(command_name)
    emit_table(rows, columns_for_format(spec, "table", rows))


def _render_wide_table(
    client: OcmoClient,
    view: NamespaceView,
    namespace: str,
    children: Sequence[Any],
    *,
    sort_by: str = "path",
    command_name: str,
) -> None:
    nodes = [item if isinstance(item, dict) else vars(item) for item in children]
    rows = enrich_ls_rows(client=client, view=view, namespace=namespace, nodes=nodes)
    sort_wide_rows(rows, sort_by)
    spec = get_command_spec(command_name)
    emit_table(rows, columns_for_format(spec, "wide", rows))
