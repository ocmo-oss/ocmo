"""Wide-format enrichment for ``ocmo ls``."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from ._output import as_dict, format_datetime

if TYPE_CHECKING:
    from ocmo import NamespaceView, OcmoClient

LS_WIDE_SORT_CHOICES = ("path", "type", "created", "updated")

_PERM_ORDER = ("r", "w", "d", "x", "t", "D", "a")

_NODE_PROBE_OPS: dict[str, dict[str, str | None]] = {
    "config": {
        "r": "config:read",
        "w": "config:write",
        "d": "config:delete",
        "x": "config:resolve",
        "t": "config:tag",
        "D": "config:describe",
        "a": "config:audit",
    },
    "template": {
        "r": "template:read",
        "w": "template:write",
        "d": "template:delete",
        "x": None,
        "t": "template:tag",
        "D": "template:describe",
        "a": "template:audit",
    },
    "secret": {
        "r": "secret:read",
        "w": "secret:write",
        "d": "secret:delete",
        "x": "secret:resolve",
        "t": "secret:tag",
        "D": "secret:describe",
        "a": "secret:audit",
    },
    "resolver": {
        "r": "resolver:read",
        "w": "resolver:write",
        "d": "resolver:delete",
        "x": None,
        "t": None,
        "D": None,
        "a": "resolver:audit",
    },
    "folder": {
        "r": None,
        "w": None,
        "d": None,
        "x": None,
        "t": None,
        "D": "folder:describe",
        "a": "folder:audit",
    },
}

_VERSIONED_NODE_TYPES = frozenset({"config", "template", "secret"})
_ITEM_METADATA_NODE_TYPES = frozenset({"resolver", "folder"})

LS_TABLE_COLUMNS = ("type", "path")
LS_WIDE_COLUMNS = ("permissions", "versions", "author", "created", "updated", "type", "path")


def basic_ls_row(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": node.get("path") or "",
        "type": node.get("node_type") or "",
    }


def probe_operations_for_node(node_type: str) -> list[str]:
    ops = _NODE_PROBE_OPS.get(node_type, {})
    return [op for letter in _PERM_ORDER if (op := ops.get(letter))]


def format_permission_string(node_type: str, allowed: dict[str, bool]) -> str:
    if node_type == "folder":
        return _format_folder_permissions(allowed)
    ops = _NODE_PROBE_OPS.get(node_type, {})
    chars: list[str] = []
    for letter in _PERM_ORDER:
        operation = ops.get(letter)
        if operation is None:
            chars.append("-")
        elif allowed.get(operation):
            chars.append(letter)
        else:
            chars.append("-")
    return "".join(chars)


def _format_folder_permissions(allowed: dict[str, bool]) -> str:
    """Folders always show read; unsettable actions use ``-`` or ``?`` (resolve)."""
    chars: list[str] = []
    for letter in _PERM_ORDER:
        if letter == "r":
            chars.append("r")
        elif letter in ("w", "d", "t"):
            chars.append("-")
        elif letter == "x":
            chars.append("?")
        elif letter == "D":
            chars.append("D" if allowed.get("folder:describe") else "-")
        elif letter == "a":
            chars.append("a" if allowed.get("folder:audit") else "-")
    return "".join(chars)


def _node_dict(node: Any) -> dict[str, Any]:
    return as_dict(node)


def _response_dict(result: Any) -> dict[str, Any]:
    return as_dict(result)


def _fetch_permissions(client: OcmoClient, *, namespace: str, path: str, node_type: str) -> str:
    operations = probe_operations_for_node(node_type)
    if not operations:
        return "-" * len(_PERM_ORDER)
    try:
        result = client.can_i(operations=operations, namespace=namespace, resource=path)
        allowed = _response_dict(result).get("allowed") or {}
    except Exception:
        return "-" * len(_PERM_ORDER)
    return format_permission_string(node_type, allowed)


def _parse_sort_datetime(value: Any) -> datetime.datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str) and value.strip() and value != "-":
        try:
            from dateutil.parser import isoparse

            return isoparse(value)
        except Exception:
            return None
    return None


def _format_timestamp(value: Any) -> str:
    return format_datetime(value) or "-"


def _fetch_versioned_fields(
    view: NamespaceView,
    *,
    path: str,
) -> tuple[str, str, str, str, datetime.datetime | None, datetime.datetime | None]:
    """Versioned items: author/created from first version, updated from latest."""
    try:
        latest_result = view.list_item_versions(path=path, limit=1)
        data = _response_dict(latest_result)
        count = data.get("versions_count")
        versions = data.get("versions") or []
        versions_text = str(count) if count is not None else "-"
        if not versions:
            return versions_text, "-", "-", "-", None, None

        latest = _node_dict(versions[0])
        updated_raw = latest.get("updated_at")
        updated = _format_timestamp(updated_raw)
        updated_at = _parse_sort_datetime(updated_raw)

        first = latest
        if isinstance(count, int) and count > 1:
            first_result = view.list_item_versions(path=path, limit=1, offset=count - 1)
            first_versions = _response_dict(first_result).get("versions") or []
            if first_versions:
                first = _node_dict(first_versions[0])

        created_raw = first.get("updated_at")
        created = _format_timestamp(created_raw)
        created_at = _parse_sort_datetime(created_raw)
        author = first.get("updater") or "-"
        return versions_text, author, created, updated, created_at, updated_at
    except Exception:
        return "-", "-", "-", "-", None, None


def _fetch_item_metadata_fields(
    view: NamespaceView,
    *,
    path: str,
) -> tuple[str, str, str, str, datetime.datetime | None, datetime.datetime | None]:
    """Non-versioned items: use ``created_at`` / ``updated_at`` from ``get_item`` when present."""
    try:
        result = view.get_item(path=path)
        data = _response_dict(result)
        author = data.get("author") or "-"
        created_raw = data.get("created_at")
        created = _format_timestamp(created_raw)
        created_at = _parse_sort_datetime(created_raw)
        updated_raw = data.get("updated_at")
        updated = _format_timestamp(updated_raw)
        updated_at = _parse_sort_datetime(updated_raw)
        return "-", author, created, updated, created_at, updated_at
    except Exception:
        return "-", "-", "-", "-", None, None


def _fetch_metadata_fields(
    view: NamespaceView,
    *,
    path: str,
    node_type: str,
) -> tuple[str, str, str, str, datetime.datetime | None, datetime.datetime | None]:
    if node_type in _VERSIONED_NODE_TYPES:
        return _fetch_versioned_fields(view, path=path)
    if node_type in _ITEM_METADATA_NODE_TYPES:
        return _fetch_item_metadata_fields(view, path=path)
    return "-", "-", "-", "-", None, None


def _sort_by_timestamp(rows: list[dict[str, Any]], field: str) -> None:
    rows.sort(
        key=lambda row: (
            row.get(field) is None,
            -(row[field].timestamp() if row.get(field) is not None else 0),
            row.get("path") or "",
        ),
    )


def sort_wide_rows(rows: list[dict[str, Any]], sort_by: str) -> None:
    """Sort wide rows in place."""
    if sort_by == "type":
        rows.sort(key=lambda row: (row.get("type") or "", row.get("path") or ""))
    elif sort_by == "created":
        _sort_by_timestamp(rows, "_created_at")
    elif sort_by == "updated":
        _sort_by_timestamp(rows, "_updated_at")
    else:
        rows.sort(key=lambda row: row.get("path") or "")


def enrich_ls_rows(
    *,
    client: OcmoClient,
    view: NamespaceView,
    namespace: str,
    nodes: Sequence[Any],
) -> list[dict[str, Any]]:
    """Build wide-format rows with per-item permission and version probes."""
    rows: list[dict[str, Any]] = []
    for node in nodes:
        item = _node_dict(node)
        path = item.get("path") or ""
        node_type = item.get("node_type") or ""
        permissions = _fetch_permissions(
            client,
            namespace=namespace,
            path=path,
            node_type=node_type,
        )
        versions, author, created, updated, created_at, updated_at = _fetch_metadata_fields(
            view,
            path=path,
            node_type=node_type,
        )
        rows.append(
            {
                "permissions": permissions,
                "versions": versions,
                "author": author,
                "created": created,
                "updated": updated,
                "_created_at": created_at,
                "_updated_at": updated_at,
                "type": node_type,
                "path": path,
            }
        )
    return rows
