"""List-mode helpers for ``ocmo get item`` (namespace-wide item listing)."""

from __future__ import annotations

from typing import Any

ITEM_NODE_TYPES: tuple[str, ...] = ("config", "template", "secret", "resolver")
GET_ITEM_TYPE_CHOICES: tuple[str, ...] = ITEM_NODE_TYPES
GET_ITEM_LIST_OUTPUT_KEY = "get item list"


def is_get_item_list_mode(*, action: str, resource: str, address: str | None) -> bool:
    return action == "get" and resource == "item" and not address


def prepare_get_item_list_extra(
    extra: dict[str, Any],
    *,
    item_types: tuple[str, ...],
) -> dict[str, Any]:
    merged = dict(extra)
    merged["types"] = list(item_types) if item_types else list(ITEM_NODE_TYPES)
    return merged
