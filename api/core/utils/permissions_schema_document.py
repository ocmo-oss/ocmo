"""Build the packaged ``_permissions.schema`` document from runtime constants."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from ..constants.permission_actions import PERMISSION_ACTION_PATTERN, PERMISSION_ACTIONS

_BUILTIN_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "data" / "builtin_schemas" / "_permissions.schema.yaml"

_ACTIONS_ITEMS_KEYS = (
    "properties",
    "policies",
    "items",
    "properties",
    "actions",
    "items",
)


def _actions_items_schema(document: dict) -> dict:
    current = document
    for key in _ACTIONS_ITEMS_KEYS:
        current = current[key]
    return current


def apply_permissions_schema_actions(document: dict) -> dict:
    """Return a copy of *document* with action enum/pattern from code constants."""
    patched = deepcopy(document)
    action_items = _actions_items_schema(patched)
    action_items["pattern"] = PERMISSION_ACTION_PATTERN
    action_items["enum"] = list(PERMISSION_ACTIONS)
    return patched


def build_permissions_schema_document() -> dict:
    """Return ``_permissions.schema`` with action enum/pattern from code constants."""
    document = yaml.safe_load(_BUILTIN_SCHEMA_PATH.read_text(encoding="utf-8"))
    return apply_permissions_schema_actions(document)


def permissions_schema_yaml() -> str:
    """Serialize the permissions schema document for storage in the tree."""
    return yaml.safe_dump(
        build_permissions_schema_document(),
        sort_keys=False,
        allow_unicode=True,
    )
