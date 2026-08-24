"""Map CLI addresses to SDK method calls for generated commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# First positional argument name when address is provided (by op_id).
_POSITIONAL_ADDRESS: dict[str, str] = {
    "show_namespace": "namespace",
    "delete_namespace": "namespace",
    "update_namespace": "namespace",
    "get_global_audit_event": "event_id",
    "get_namespace_audit_event": "event_id",
    "get_global_permission": "rule_id",
    "delete_global_permission": "rule_id",
    "update_global_permission": "rule_id",
    "move_global_permission": "rule_id",
    "get_lock": "path",
    "create_lock": "path",
    "replace_lock": "path",
    "delete_lock": "path",
    "set_tag": "path",
}

# Keyword name for address when not using default ``path``.
_KEYWORD_ADDRESS: dict[str, str] = {
    "create_namespace": "name",
    "create_global_permission": "id",
}

# Create/update ops whose ADDRESS is not a tree path (skip segment validation).
NON_TREE_ADDRESS_OPS = frozenset(
    {
        "create_namespace",
        "create_global_permission",
    }
)

# Operations with multiple positional arguments after kwargs are assembled.
_MULTI_POSITIONAL: dict[str, list[str]] = {}


@dataclass(frozen=True)
class SdkExtraParam:
    """Extra CLI flag mapped to an SDK keyword argument."""

    sdk_name: str
    click_name: str
    help: str
    type_: type | None = str
    is_flag: bool = False


_SDK_PARAM_CATALOG: dict[str, SdkExtraParam] = {
    "q": SdkExtraParam("q", "q", "Search query string."),
    "types": SdkExtraParam("types", "types", "Filter by node types (comma-separated)."),
    "limit": SdkExtraParam("limit", "limit", "Maximum number of results.", int),
    "offset": SdkExtraParam("offset", "offset", "Result offset for pagination.", int),
    "object_id": SdkExtraParam("object_id", "object-id", "Audit object ID."),
    "object_type": SdkExtraParam("object_type", "object-type", "Audit object type."),
    "search": SdkExtraParam("search", "search", "Free-text search filter."),
    "from_": SdkExtraParam("from_", "from", "Range start (ISO timestamp)."),
    "to": SdkExtraParam("to", "to", "Range end (ISO timestamp)."),
    "bucket_seconds": SdkExtraParam("bucket_seconds", "bucket-seconds", "Bucket size in seconds.", int),
    "tag": SdkExtraParam("tag", "tag", "Version tag name."),
    "no_creds": SdkExtraParam("no_creds", "no-creds", "Omit credential-backed parameters.", is_flag=True),
    "auth_id": SdkExtraParam("auth_id", "auth-id", "Filter by author ID."),
    "auth_email": SdkExtraParam("auth_email", "auth-email", "Filter by author email."),
    "event_id": SdkExtraParam("event_id", "event-id", "Filter by event ID."),
    "event_kind": SdkExtraParam("event_kind", "event-kind", "Filter by event kind."),
    "token_number": SdkExtraParam("token_number", "token-number", "Resolver token number.", int),
    "reason": SdkExtraParam("reason", "reason", "Lock rationale."),
    "expires_at": SdkExtraParam("expires_at", "expires-at", "Lock expiry time (ISO-8601 UTC)."),
    "position": SdkExtraParam(
        "position",
        "position",
        "Sort position for the new rule (applied via move after create).",
        float,
    ),
    "description": SdkExtraParam(
        "description",
        "description",
        "Human-readable namespace description.",
    ),
    "tagged_only": SdkExtraParam(
        "tagged_only",
        "tagged-only",
        "Show only versions that have tags.",
        is_flag=True,
    ),
    "preview": SdkExtraParam(
        "preview",
        "preview",
        "Show what would be deleted without removing anything.",
        is_flag=True,
    ),
}

# Per-operation extra SDK kwargs exposed as CLI flags.
_OP_EXTRA_PARAMS: dict[str, list[str]] = {
    "search_root": ["q", "types", "limit", "offset"],
    "search_path": ["q", "types", "limit", "offset"],
    "namespace_audit_timeline": ["object_id", "object_type", "search", "limit", "offset"],
    "namespace_audit_resolve_series": ["object_id", "object_type", "from_", "to", "bucket_seconds"],
    "list_namespace_audit": [
        "auth_id",
        "auth_email",
        "object_id",
        "object_type",
        "event_id",
        "event_kind",
        "search",
        "from_",
        "to",
        "limit",
        "offset",
    ],
    "list_global_audit": [
        "auth_id",
        "auth_email",
        "object_id",
        "object_type",
        "event_id",
        "event_kind",
        "search",
        "from_",
        "to",
        "limit",
        "offset",
    ],
    "set_tag": ["tag"],
    "rotate_resolver_token": ["token_number"],
    "create_lock": ["reason", "expires_at"],
    "replace_lock": ["reason", "expires_at"],
    "create_namespace": ["description"],
    "create_global_permission": ["position"],
    "list_item_versions": ["limit", "offset", "tagged_only"],
    "delete_item": ["preview"],
}

# Operations that accept version/tag via address@VER or --version.
VERSION_ADDRESS_OPS = frozenset(
    {
        "get_item",
        "delete_item",
        "propagate_config",
        "get_config_data_schema",
        "set_tag",
    }
)

# ADDRESS@VER is folded into the request body (not an SDK ``version`` kwarg).
VERSION_BODY_OPS = frozenset(
    {
        "set_tag",
    }
)

# ADDRESS@VER is a filter/query for these ops, not an SDK ``version`` argument.
VERSION_FILTER_OPS = frozenset(
    {
        "list_item_versions",
    }
)

# Operations that do not accept a tree path / address argument.
NO_ADDRESS_OPS = frozenset(
    {
        "namespace_audit_timeline",
        "namespace_audit_resolve_series",
        "search_root",
        "list_namespaces",
        "list_global_audit",
        "list_namespace_audit",
        "list_global_permissions",
        "list_locks",
        "list_cast_formats",
        "health",
    }
)


def address_optional_for_command(
    op_ids: list[str],
    *,
    action: str,
    resource: str,
) -> bool:
    """True when ADDRESS may be omitted (list-without-path or scoped list ops)."""
    if action == "create" and resource == "globalpermission":
        return True
    if action == "get" and resource in ("item", "cast"):
        return True
    return any(op_id in NO_ADDRESS_OPS for op_id in op_ids)


def address_required_for_op(op_id: str, *, action: str, resource: str) -> bool:
    """True when the resolved SDK operation needs a CLI ADDRESS."""
    if action == "create" and resource == "globalpermission":
        return False
    return op_id not in NO_ADDRESS_OPS


def extra_params_for_ops(op_ids: list[str]) -> list[SdkExtraParam]:
    """Return sorted unique extra parameter specs for a generated command."""
    seen: dict[str, SdkExtraParam] = {}
    for op_id in op_ids:
        for name in _OP_EXTRA_PARAMS.get(op_id, []):
            seen[name] = _SDK_PARAM_CATALOG[name]
    return [seen[k] for k in sorted(seen)]


def pick_op_id(
    op_ids: list[str],
    *,
    address: str | None,
    namespace: str | None,
    ops_meta: dict[str, dict[str, Any]],
) -> str:
    """Choose the SDK operation when several map to the same CLI command."""
    if len(op_ids) == 1:
        return op_ids[0]

    candidates = list(op_ids)

    # Mixed client/namespace audit & permission ops: prefer scope matching -n.
    if namespace:
        scoped = [o for o in candidates if ops_meta.get(o, {}).get("scope") == "namespace"]
        if scoped:
            candidates = scoped
    else:
        scoped = [o for o in candidates if ops_meta.get(o, {}).get("scope") == "client"]
        if scoped:
            candidates = scoped

    if address:
        singles = [
            o
            for o in candidates
            if o.startswith(("show_", "get_", "search_path", "navigate_path")) or o.endswith("_path")
        ]
        if singles:
            return singles[0]
        non_list = [o for o in candidates if not o.startswith("list_") and not o.endswith("_root")]
        return non_list[0] if non_list else candidates[0]

    lists = [o for o in candidates if o.startswith("list_") or o.endswith("_root")]
    return lists[0] if lists else candidates[0]


def address_keyword_for_op(op_id: str) -> str:
    """SDK keyword that receives the CLI ADDRESS for ``op_id``."""
    return _KEYWORD_ADDRESS.get(op_id, "path")


def build_sdk_call(
    op_id: str,
    *,
    path: str | None,
    version: str | None,
    content: str | None,
    extra: dict[str, Any] | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    """Return (positional_args, keyword_args) for an SDK facade method."""
    from ocmo._facade_meta import DOCUMENT_BODY_OPS

    args: list[Any] = []
    kwargs: dict[str, Any] = {}

    if path is not None:
        if op_id in _POSITIONAL_ADDRESS:
            args.append(path)
        else:
            kw = address_keyword_for_op(op_id)
            kwargs[kw] = path

    if version is not None and op_id not in VERSION_FILTER_OPS and op_id not in VERSION_BODY_OPS:
        kwargs["version"] = version

    if content is not None:
        if op_id in DOCUMENT_BODY_OPS:
            kwargs["content"] = content
        else:
            kwargs["body"] = content

    if extra:
        for key, value in extra.items():
            if value is not None and value is not False:
                kwargs[key] = value

    multi = _MULTI_POSITIONAL.get(op_id)
    if multi:
        for name in multi:
            if name in kwargs:
                args.append(kwargs.pop(name))

    return args, kwargs


def unwrap_list_payload(data: Any) -> list[dict[str, Any]] | None:
    """Extract a list of row dicts from common paginated API responses."""
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in ("items", "children", "versions", "locks", "rules", "formats"):
            value = data.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    return None
