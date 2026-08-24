"""Read OCMO export metadata from files (xattrs and comment headers)."""

from __future__ import annotations

import os
import re
from pathlib import Path

from ._export_metadata import _XATTR_PREFIX

_YAML_META_RE = re.compile(r"^#\s*([^:]+):\s*(.*)$")
_JINJA_META_RE = re.compile(r"^\{#\s*([^:]+):\s*(.*?)\s*#\}$")

# Keys written by ``ocmo export --metadata`` (see ``item_metadata_rows``).
EXPORT_METADATA_KEYS = frozenset(
    {
        "namespace",
        "path",
        "name",
        "node_type",
        "author",
        "version",
        "updater",
        "updated_at",
        "description",
        "deleted_at",
        "deleted_by",
    }
)


def read_file_metadata(path: Path) -> dict[str, str]:
    """Read ``user.ocmo.*`` xattrs and leading comment metadata from *path*."""
    meta = _read_xattr_metadata(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    for key, value in _parse_leading_comment_metadata(text).items():
        meta.setdefault(key, value)
    return meta


def import_file_text(content_bytes: bytes) -> str:
    """Decode file bytes and strip leading export metadata comments."""
    text = content_bytes.decode("utf-8", errors="replace")
    return strip_export_metadata_comments(text)


def strip_export_metadata_comments(content: str) -> str:
    """Remove leading export metadata comment lines from *content*."""
    if not content:
        return content

    lines = content.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        line = lines[index].rstrip("\n")
        if _is_export_metadata_comment_line(line):
            index += 1
            continue
        break
    return "".join(lines[index:])


def strip_leading_metadata_comments(content: str, *, node_type: str) -> str:
    """Backward-compatible alias for :func:`strip_export_metadata_comments`."""
    return strip_export_metadata_comments(content)


def metadata_tree_path(metadata_path: str, target_prefix: str) -> str:
    """Join optional ``--to`` prefix with the path from metadata."""
    item_path = metadata_path.strip("/")
    prefix = target_prefix.strip("/")
    if prefix and item_path:
        return f"{prefix}/{item_path}"
    if prefix:
        return prefix
    return item_path


def _read_xattr_metadata(path: Path) -> dict[str, str]:
    if not hasattr(os, "listxattr"):
        return {}

    try:
        names = os.listxattr(path)
    except OSError:
        return {}

    meta: dict[str, str] = {}
    for name in names:
        if not isinstance(name, str) or not name.startswith(_XATTR_PREFIX):
            continue
        key = name[len(_XATTR_PREFIX) :]
        try:
            value = os.getxattr(path, name)
        except OSError:
            continue
        if isinstance(value, bytes):
            meta[key] = value.decode("utf-8", errors="replace")
        else:
            meta[key] = str(value)
    return meta


def _parse_metadata_comment_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    parsed_yaml = _YAML_META_RE.match(stripped)
    if parsed_yaml:
        return parsed_yaml.group(1).strip()
    parsed_jinja = _JINJA_META_RE.match(stripped)
    if parsed_jinja:
        return parsed_jinja.group(1).strip()
    return None


def _is_export_metadata_comment_line(line: str) -> bool:
    key = _parse_metadata_comment_key(line)
    return key is not None and key in EXPORT_METADATA_KEYS


def _parse_leading_comment_metadata(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        key = _parse_metadata_comment_key(stripped)
        if key is None or key not in EXPORT_METADATA_KEYS:
            break
        parsed_yaml = _YAML_META_RE.match(stripped)
        if parsed_yaml:
            meta[key] = parsed_yaml.group(2).strip()
            continue
        parsed_jinja = _JINJA_META_RE.match(stripped)
        if parsed_jinja:
            meta[key] = parsed_jinja.group(2).strip()
            continue
        break
    return meta
