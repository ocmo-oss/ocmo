"""Capability flags for built-in and ordinary namespace tree items."""

from __future__ import annotations

from dataclasses import dataclass

# Canonical registry — imported by TreeManager, permissions.check_tree, namespace init.
BUILTIN_NAMESPACE_CONFIG_PATHS = frozenset(
    {
        "_permissions",
        "_webhooks",
        "_git_sync",
    }
)
BUILTIN_NAMESPACE_SCHEMA_CONFIG_PATHS = frozenset(f"{path}.schema" for path in BUILTIN_NAMESPACE_CONFIG_PATHS)
BUILTIN_NAMESPACE_SECRET_PATHS = frozenset(
    {
        "_webhooks_secret",
        "_git_sync_secret",
    }
)
BUILTIN_NAMESPACE_PATHS = (
    BUILTIN_NAMESPACE_CONFIG_PATHS | BUILTIN_NAMESPACE_SECRET_PATHS | BUILTIN_NAMESPACE_SCHEMA_CONFIG_PATHS
)

BUILTIN_NAMESPACE_PATH_ORDER = (
    "_permissions",
    "_permissions.schema",
    "_webhooks",
    "_webhooks_secret",
    "_webhooks.schema",
    "_git_sync",
    "_git_sync_secret",
    "_git_sync.schema",
)

COMPANION_SECRET_PARENT: dict[str, str] = {
    "_webhooks_secret": "_webhooks",
    "_git_sync_secret": "_git_sync",
}


def normalize_tree_path(path: str) -> str:
    return path.strip("/")


def builtin_namespace_paths_payload() -> dict:
    """Builtin namespace tree paths for client bootstrap via ``/api/version``."""
    return {
        "config": sorted(BUILTIN_NAMESPACE_CONFIG_PATHS),
        "secret": sorted(BUILTIN_NAMESPACE_SECRET_PATHS),
        "schema": sorted(BUILTIN_NAMESPACE_SCHEMA_CONFIG_PATHS),
        "order": list(BUILTIN_NAMESPACE_PATH_ORDER),
    }


def reserved_tags_payload() -> dict[str, list[str]]:
    """Reserved version tag names per item type for client bootstrap."""
    from .tree.constants import _RESERVED_TAGS

    return {item_type: sorted(tags) for item_type, tags in _RESERVED_TAGS.items()}


def is_builtin_namespace_path(path: str) -> bool:
    return normalize_tree_path(path) in BUILTIN_NAMESPACE_PATHS


def is_builtin_namespace_config_path(path: str) -> bool:
    return normalize_tree_path(path) in BUILTIN_NAMESPACE_CONFIG_PATHS


def is_builtin_namespace_schema_config_path(path: str) -> bool:
    return normalize_tree_path(path) in BUILTIN_NAMESPACE_SCHEMA_CONFIG_PATHS


@dataclass(frozen=True)
class TreeItemCapabilities:
    is_visible: bool = True
    is_readable: bool = True
    is_writable: bool = True
    is_deletable: bool = True
    is_movable: bool = True
    is_copyable: bool = True
    is_creatable: bool = True
    is_resolvable: bool = True
    is_folder_resolvable: bool = True
    is_direct_resolve_target: bool = True
    is_extend_target: bool = True
    is_available_for_param: bool = True


_ALL_TRUE = TreeItemCapabilities()


def _has_namespace_write(auth, namespace) -> bool:
    if auth is None:
        return True
    if namespace is None:
        return False
    return auth.permissions(namespace).check_namespace_object(namespace.name, "write")


def _is_in_resolver_scope(auth, path: str) -> bool:
    """True when path is the resolver scope root or a descendant."""
    if auth is None or not auth.is_resolver:
        return True
    normalized = normalize_tree_path(path)
    scope = auth.access_scope or ""
    if not scope:
        return True
    return normalized == scope or normalized.startswith(scope + "/")


def _is_in_resolver_direct_scope(auth, path: str) -> bool:
    """True when a resolver may use path as a direct resolve target."""
    return _is_in_resolver_scope(auth, path)


def compute_tree_capabilities(
    namespace,
    path: str,
    auth,
    *,
    referencing_config_path: str | None = None,
) -> TreeItemCapabilities:
    """Return capability flags for one tree path and caller identity."""
    if auth is None:
        return _ALL_TRUE

    normalized = normalize_tree_path(path)
    if normalized not in BUILTIN_NAMESPACE_PATHS:
        in_scope = _is_in_resolver_scope(auth, normalized)
        return TreeItemCapabilities(
            is_visible=in_scope,
            is_direct_resolve_target=in_scope,
        )

    has_write = _has_namespace_write(auth, namespace)

    if normalized in BUILTIN_NAMESPACE_SCHEMA_CONFIG_PATHS:
        return TreeItemCapabilities(
            is_visible=has_write,
            is_readable=has_write,
            is_writable=False,
            is_deletable=False,
            is_movable=False,
            is_copyable=False,
            is_creatable=False,
            is_resolvable=False,
            is_folder_resolvable=False,
            is_direct_resolve_target=False,
            is_extend_target=False,
            is_available_for_param=False,
        )

    if normalized in BUILTIN_NAMESPACE_CONFIG_PATHS:
        can_resolve = has_write and not auth.is_resolver
        return TreeItemCapabilities(
            is_visible=has_write,
            is_readable=has_write,
            is_writable=has_write,
            is_deletable=False,
            is_movable=False,
            is_copyable=False,
            is_creatable=False,
            is_resolvable=can_resolve,
            is_folder_resolvable=False,
            is_direct_resolve_target=can_resolve,
            is_extend_target=False,
            is_available_for_param=False,
        )

    # Companion secret
    allowed_parent = COMPANION_SECRET_PARENT.get(normalized)
    param_ok = referencing_config_path is not None and normalize_tree_path(referencing_config_path) == allowed_parent
    return TreeItemCapabilities(
        is_visible=has_write,
        is_readable=has_write,
        is_writable=has_write,
        is_deletable=False,
        is_movable=False,
        is_copyable=False,
        is_creatable=False,
        is_resolvable=False,
        is_folder_resolvable=False,
        is_direct_resolve_target=False,
        is_extend_target=False,
        is_available_for_param=param_ok,
    )
