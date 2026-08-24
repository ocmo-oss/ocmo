"""Lightweight registry for generated CLI action groups.

Keeps action names and help text available without importing generated.py.
Help strings here must stay import-light (no generated.py or SDK).
"""

from __future__ import annotations

_GENERATED_ACTION_HELP: dict[str, str] = {
    "get": "Retrieve API resources.",
    "create": "Create new resources.",
    "update": "Update existing resources.",
    "delete": "Delete resources.",
    "tag": "Add a version tag to an item.",
    "untag": "Remove a version tag from an item.",
    "rotate": "Rotate resolver access tokens.",
    "propagate": "Propagate an item to descendant paths.",
    "search": "Search the item tree.",
}


def generated_action_names() -> list[str]:
    """Return sorted action names for generated command groups."""
    from ocmo_cli._commands_map import OPERATIONS

    actions: set[str] = set()
    has_set_tag = False
    for config in OPERATIONS.values():
        if not isinstance(config, dict):
            continue
        if config.get("hand_written") or config.get("skip"):
            continue
        action = config.get("action")
        if not action or action == "resolve":
            continue
        actions.add(action)
        if action == "tag":
            has_set_tag = True
    if has_set_tag:
        actions.add("untag")
    return sorted(actions)


def action_help(action: str) -> str:
    return _GENERATED_ACTION_HELP.get(action, f"{action.capitalize()} resources.")
