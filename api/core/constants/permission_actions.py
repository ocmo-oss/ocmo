"""Permission policy action strings accepted in ``_permissions`` configs."""

from __future__ import annotations

PERMISSION_ACTION_RESOURCES = ("config", "template", "resolver", "secret", "lock", "folder", "*")
PERMISSION_ACTION_VERBS = ("read", "write", "delete", "resolve", "tag", "describe", "audit", "*")

# Concrete ``<resource>:<verb>`` pairs enforced by namespace ABAC (tree managers / can-i probes).
PERMISSION_CONCRETE_ACTIONS: tuple[str, ...] = (
    "config:read",
    "config:write",
    "config:delete",
    "config:resolve",
    "config:tag",
    "config:describe",
    "config:audit",
    "template:read",
    "template:write",
    "template:delete",
    "template:tag",
    "template:describe",
    "template:audit",
    "resolver:read",
    "resolver:write",
    "resolver:delete",
    "resolver:audit",
    "secret:read",
    "secret:write",
    "secret:delete",
    "secret:resolve",
    "secret:tag",
    "secret:describe",
    "secret:audit",
    "lock:read",
    "lock:write",
    "lock:delete",
    "folder:describe",
    "folder:audit",
)

PERMISSION_RESOURCE_WILDCARD_ACTIONS: tuple[str, ...] = tuple(
    f"{resource}:*" for resource in ("config", "template", "resolver", "secret", "lock")
)

PERMISSION_VERB_WILDCARD_ACTIONS: tuple[str, ...] = tuple(
    f"*:{verb}" for verb in ("read", "write", "delete", "resolve", "tag", "describe", "audit")
)

PERMISSION_ACTIONS: tuple[str, ...] = (
    *PERMISSION_CONCRETE_ACTIONS,
    *PERMISSION_RESOURCE_WILDCARD_ACTIONS,
    *PERMISSION_VERB_WILDCARD_ACTIONS,
    "*:*",
)

PERMISSION_ACTION_PATTERN = (
    r"^(config|template|resolver|secret|lock|folder|\*):"
    r"(read|write|delete|resolve|tag|describe|audit|\*)$"
)
