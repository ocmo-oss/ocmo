from __future__ import annotations

from ..tree_capabilities import (
    BUILTIN_NAMESPACE_CONFIG_PATHS,
    BUILTIN_NAMESPACE_PATHS,
    BUILTIN_NAMESPACE_SECRET_PATHS,
    COMPANION_SECRET_PARENT,
)
from .base import TreeManagerBaseMixin
from .config_ops import TreeConfigOpsMixin
from .constants import TreeItemLike
from .create import TreeCreateMixin
from .diff import TreeDiffMixin
from .mutate import TreeMutateMixin
from .paths import TreePathMixin
from .propagation import TreePropagationMixin
from .read import TreeReadMixin
from .resolver_ops import TreeResolverOpsMixin
from .tags import TreeTagsMixin
from .update import TreeUpdateMixin
from .versions import TreeVersionsMixin


class TreeManager(
    TreePropagationMixin,
    TreeConfigOpsMixin,
    TreeTagsMixin,
    TreeDiffMixin,
    TreeResolverOpsMixin,
    TreeMutateMixin,
    TreeUpdateMixin,
    TreeVersionsMixin,
    TreeReadMixin,
    TreeCreateMixin,
    TreePathMixin,
    TreeManagerBaseMixin,
):
    BUILTIN_NAMESPACE_CONFIG_PATHS = BUILTIN_NAMESPACE_CONFIG_PATHS
    BUILTIN_NAMESPACE_SECRET_PATHS = BUILTIN_NAMESPACE_SECRET_PATHS
    BUILTIN_NAMESPACE_PATHS = BUILTIN_NAMESPACE_PATHS
    COMPANION_SECRET_PARENT = COMPANION_SECRET_PARENT

    valid_operations = [
        "list",
        "search",
        "get",
        "create",
        "update",
        "delete",
        "move",
        "copy",
    ]
    item = None
    item_type = "item"

    def __init__(self, namespace, path, *, auth, referencing_config_path=None):
        self._bootstrap(
            namespace,
            path=path,
            item=None,
            auth=auth,
            referencing_config_path=referencing_config_path,
        )

    @classmethod
    def for_item(
        cls,
        namespace,
        item: TreeItemLike,
        *,
        auth,
        referencing_config_path=None,
    ) -> TreeManager:
        instance = cls.__new__(cls)
        instance._bootstrap(
            namespace,
            path=None,
            item=item,
            auth=auth,
            referencing_config_path=referencing_config_path,
        )
        return instance


__all__ = ["TreeManager", "TreeItemLike"]
