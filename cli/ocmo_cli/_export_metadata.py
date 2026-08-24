"""Export metadata comments and extended attributes."""

from __future__ import annotations

import os
from typing import Any

from ._item_output import item_metadata_rows

_XATTR_PREFIX = "user.ocmo."


def export_metadata_rows(raw_item: Any, *, namespace: str) -> list[tuple[str, Any]]:
    """Metadata key/value pairs to embed in exports."""
    rows = item_metadata_rows(raw_item)
    if namespace:
        rows = [("namespace", namespace), *rows]
    return rows


def metadata_file_prefix(rows: list[tuple[str, Any]], *, node_type: str) -> str:
    """Return a comment block to prepend to exported file content."""
    if not rows or node_type == "secret":
        return ""

    lines: list[str] = []
    for key, value in rows:
        text = f"{key}: {value}"
        if node_type == "template":
            lines.append(f"{{# {text} #}}")
        else:
            lines.append(f"# {text}")

    return "\n".join(lines) + "\n"


def write_export_xattrs(path: os.PathLike[str] | str, rows: list[tuple[str, Any]]) -> None:
    """Best-effort write of export metadata to ``user.ocmo.*`` xattrs."""
    if not rows or not hasattr(os, "setxattr"):
        return

    for key, value in rows:
        attr = f"{_XATTR_PREFIX}{key}"
        try:
            os.setxattr(path, attr, str(value).encode("utf-8"))
        except OSError:
            continue
