"""Normalize config document bodies before upload."""

from __future__ import annotations

import json
from typing import Any

from ._output import yaml_dumps

_CONFIG_METADATA_KEY = "_ocmo"


def prepare_config_apply_content(content: str, *, source_name: str) -> str:
    """Convert JSON config sources to YAML syntax for storage."""
    if not _is_json_config_source(source_name, content):
        return content

    try:
        doc = json.loads(content)
    except json.JSONDecodeError:
        return content

    if isinstance(doc, dict):
        _inject_json_cast_metadata(doc)

    return yaml_dumps(doc)


def _is_json_config_source(source_name: str, content: str) -> bool:
    if source_name != "<stdin>":
        return source_name.lower().endswith(".json")
    stripped = content.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _inject_json_cast_metadata(doc: dict[str, Any]) -> None:
    """Preserve JSON resolve semantics when the on-disk source was JSON."""
    existing = doc.get(_CONFIG_METADATA_KEY)
    cast_block = {"format": "json"}
    if existing is None:
        doc[_CONFIG_METADATA_KEY] = {"cast": cast_block}
    elif isinstance(existing, dict) and "cast" not in existing:
        doc[_CONFIG_METADATA_KEY] = {**existing, "cast": cast_block}
