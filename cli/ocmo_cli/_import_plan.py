"""Import plan building and validation."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._import_metadata import import_file_text, metadata_tree_path, read_file_metadata

if TYPE_CHECKING:
    from ocmo import NamespaceView

VALID_IMPORT_TYPES = frozenset({"config", "template", "secret", "resolver"})


def try_parse_config_document(content_bytes: bytes) -> tuple[dict[str, Any] | None, bool]:
    """Return ``(document, is_json)`` when *content_bytes* is a YAML/JSON object."""
    text = content_bytes.decode("utf-8", errors="replace")
    try:
        doc = json.loads(text)
        if isinstance(doc, dict):
            return doc, True
    except json.JSONDecodeError:
        pass

    import yaml  # deferred

    try:
        doc = yaml.safe_load(text)
    except Exception:
        return None, False
    if isinstance(doc, dict):
        return doc, False
    return None, False


def classify_file_kind(content_bytes: bytes) -> str:
    """Classify a source file as ``config`` or ``template`` by parsing content."""
    doc, _ = try_parse_config_document(content_bytes)
    return "config" if doc is not None else "template"


def parse_type_override(spec: str) -> tuple[str, str]:
    """Parse ``GLOB=TYPE`` from ``--type-override``."""
    if "=" not in spec:
        raise ValueError(f"expected GLOB=TYPE, got {spec!r}")
    pattern, item_type = spec.split("=", 1)
    pattern = pattern.strip()
    item_type = item_type.strip().lower()
    if not pattern:
        raise ValueError(f"type override pattern must not be empty in {spec!r}")
    _validate_import_type(item_type)
    return pattern, item_type


def load_type_map(path: Path) -> list[tuple[str, str]]:
    """Load glob → item-type mappings from a YAML file."""
    import yaml  # deferred

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(raw, dict) and "types" in raw:
        raw = raw["types"]
    if not isinstance(raw, dict):
        raise ValueError(f"type map {path} must be a YAML mapping")

    mappings: list[tuple[str, str]] = []
    for pattern, item_type in raw.items():
        pattern = str(pattern).strip()
        item_type = str(item_type).strip().lower()
        if not pattern:
            raise ValueError(f"type map {path} contains an empty pattern")
        _validate_import_type(item_type)
        mappings.append((pattern, item_type))
    return mappings


def explicit_import_type(
    rel_str: str,
    *,
    type_map: list[tuple[str, str]],
    type_overrides: list[tuple[str, str]],
) -> str | None:
    """Return the explicitly mapped type for *rel_str*, if any."""
    resolved: str | None = None
    for pattern, item_type in [*type_map, *type_overrides]:
        if _matches_glob(rel_str, pattern):
            resolved = item_type
    return resolved


def resolve_import_type(
    rel_str: str,
    *,
    type_map: list[tuple[str, str]],
    type_overrides: list[tuple[str, str]],
    metadata_type: str | None,
    content_bytes: bytes,
) -> str:
    """Pick the import item type for a source file."""
    resolved = explicit_import_type(
        rel_str,
        type_map=type_map,
        type_overrides=type_overrides,
    )
    if resolved:
        return resolved
    if metadata_type:
        _validate_import_type(metadata_type)
        return metadata_type
    return classify_file_kind(content_bytes)


def _validate_import_type(item_type: str) -> None:
    if item_type not in VALID_IMPORT_TYPES:
        allowed = ", ".join(sorted(VALID_IMPORT_TYPES))
        raise ValueError(f"invalid item type {item_type!r}; expected one of: {allowed}")


def _matches_glob(rel_str: str, pattern: str) -> bool:
    return fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(Path(rel_str).name, pattern)


def annotate_plan_conflicts(
    plan: list[dict[str, Any]],
    *,
    namespace: str,
    update: bool,
    view: NamespaceView | None = None,
) -> list[str]:
    """Mark conflicting entries and return human-readable conflict messages."""
    messages: list[str] = []
    seen_paths: dict[str, str] = {}

    for entry in plan:
        entry.setdefault("status", "ok")
        entry.setdefault("action", "create")
        entry.pop("conflict", None)

        if entry.get("conflict_reason"):
            entry["status"] = "conflict"
            entry["conflict"] = entry["conflict_reason"]
            messages.append(f"{entry['source_rel']}: {entry['conflict_reason']}")
            continue

        tree_path = entry["tree_path"]
        rel = str(entry["source_rel"])
        if tree_path in seen_paths:
            reason = f"tree path {tree_path!r} is already mapped from {seen_paths[tree_path]!r}"
            entry["status"] = "conflict"
            entry["conflict"] = reason
            messages.append(f"{rel}: {reason}")
            continue
        seen_paths[tree_path] = rel

        meta_ns = entry.get("metadata_namespace")
        if meta_ns and meta_ns != namespace:
            reason = f"metadata namespace {meta_ns!r} does not match {namespace!r}"
            entry["status"] = "conflict"
            entry["conflict"] = reason
            messages.append(f"{rel}: {reason}")

        if view is not None:
            exists = _item_exists(view, tree_path)
            if exists:
                entry["action"] = "update"
                if not update:
                    reason = f"item {tree_path!r} already exists (use --update)"
                    entry["status"] = "conflict"
                    entry["conflict"] = reason
                    messages.append(f"{rel}: {reason}")

    return messages


def build_metadata_entry(
    *,
    file_path: Path,
    rel: Path,
    rel_str: str,
    target_prefix: str,
    content_bytes: bytes,
    type_map: list[tuple[str, str]],
    type_overrides: list[tuple[str, str]],
) -> dict[str, Any] | None:
    """Build one import plan entry from export metadata on *file_path*."""
    meta = read_file_metadata(file_path)
    item_path = meta.get("path", "").strip()
    if not item_path:
        return None

    metadata_type = meta.get("node_type", "").strip() or None
    node_type = resolve_import_type(
        rel_str,
        type_map=type_map,
        type_overrides=type_overrides,
        metadata_type=metadata_type,
        content_bytes=content_bytes,
    )
    tree_path = metadata_tree_path(item_path, target_prefix)
    body = import_file_text(content_bytes)

    entry: dict[str, Any] = {
        "kind": node_type,
        "source_rel": rel,
        "source_abs": file_path,
        "tree_path": tree_path,
        "metadata_namespace": meta.get("namespace", "").strip() or None,
        "content": body,
    }

    return entry


def _item_exists(view: NamespaceView, path: str) -> bool:
    try:
        view.get_item(path=path)
        return True
    except Exception:
        return False
