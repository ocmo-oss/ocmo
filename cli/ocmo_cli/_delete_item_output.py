"""Output formatting for ``ocmo delete item``."""

from __future__ import annotations

import re
from typing import Any

from ._output import emit, emit_table
from ._output_manifest import get_command_spec, resolve_effective_format

_DELETE_PREVIEW_RE = re.compile(r"^[^:]+::\s*(\w+)::\s*(.+)$")

_TYPE_BY_LABEL = {
    "folder": "folder",
    "config": "config",
    "template": "template",
    "secret": "secret",
    "resolver": "resolver",
}


def _split_path_version(raw_path: str) -> tuple[str, int | None]:
    if "@" not in raw_path:
        return raw_path, None
    path, suffix = raw_path.rsplit("@", 1)
    if suffix.isdigit():
        return path, int(suffix)
    return raw_path, None


def parse_delete_preview_line(line: str) -> dict[str, Any]:
    """Parse API delete lines like ``my-ns:: Config:: app/foo``."""
    trimmed = line.strip()
    match = _DELETE_PREVIEW_RE.match(trimmed)
    if not match:
        path = trimmed
        node_type = "config"
    else:
        node_type = _TYPE_BY_LABEL.get(match[1].lower(), "config")
        path = match[2]

    path, version_number = _split_path_version(path)
    name = path.rsplit("/", 1)[-1] if path else path
    entry: dict[str, Any] = {"path": path, "name": name, "node_type": node_type}
    if version_number is not None:
        entry["version"] = version_number
    return entry


def parse_delete_preview_lines(lines: list[str]) -> list[dict[str, Any]]:
    return [parse_delete_preview_line(line) for line in lines]


def _normalize_path(path: str) -> str:
    return path.strip("/")


def is_folder_delete(entries: list[dict[str, Any]], target_path: str | None) -> bool:
    if not target_path:
        return False
    norm = _normalize_path(target_path)
    return any(
        entry.get("node_type") == "folder" and _normalize_path(entry.get("path") or "") == norm for entry in entries
    )


def delete_item_table_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        row: dict[str, Any] = {
            "type": entry.get("node_type") or "",
            "path": entry.get("path") or "",
        }
        if entry.get("version") is not None:
            row["version"] = entry["version"]
        rows.append(row)
    rows.sort(key=lambda row: (row["path"], row.get("version") or 0))
    return rows


def delete_item_table_columns(rows: list[dict[str, Any]]) -> list[str]:
    if any(row.get("version") is not None for row in rows):
        return ["type", "version", "path"]
    return ["type", "path"]


def emit_delete_item_output(
    result: Any,
    *,
    target_path: str | None,
    version: str | None,
    output_fmt: str | None,
    ctx_fmt: str | None,
) -> None:
    """Render delete results as ``ocmo tree`` (folders) or ``ocmo ls`` (other items)."""
    from .commands.ls import _build_tree_hierarchy, _render_plain_tree

    command_key = "delete item"
    spec = get_command_spec(command_key)
    effective_fmt = resolve_effective_format(output_fmt, ctx_fmt, spec)

    delete_lines = list(getattr(result, "delete", None) or [])
    entries = parse_delete_preview_lines(delete_lines)

    use_tree = effective_fmt == "table" and version is None and is_folder_delete(entries, target_path)

    if use_tree:
        tree_rows = _build_tree_hierarchy(entries)
        _render_plain_tree(tree_rows, prefix="", connector="", use_emoji=False)
        return

    rows = delete_item_table_rows(entries)

    if effective_fmt == "table":
        emit_table(rows, delete_item_table_columns(rows))
        return

    if effective_fmt == "name":
        for entry in entries:
            print(entry.get("path") or "")
        return

    if effective_fmt == "path":
        for entry in entries:
            print(entry.get("path") or "")
        return

    payload = {"delete": entries}
    emit(payload, effective_fmt)
