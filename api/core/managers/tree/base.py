from ._common import *
from .mutate import TreeMutateMixin


class TreeManagerBaseMixin:
    def _bootstrap(
        self,
        namespace,
        *,
        path: str | None,
        item: TreeItemLike | None,
        auth,
        referencing_config_path=None,
    ) -> None:
        self.namespace = namespace
        self.auth = auth
        self._referencing_config_path = referencing_config_path

        if item is not None:
            if item.namespace_id != namespace.pk:
                raise ValidationError("item namespace does not match TreeManager namespace")
            self.path = item.path.removesuffix("/")
            validate_path_characters(self.path, allow_root=True)
            self.item = self._cast_to_specific(item)
            self.item_type = "folder" if self.item.node_type == "folder" else "item"
        elif path == "":
            validate_path_characters(path, allow_root=True)
            self.item_type = "root"
            self.path = path
            self.item = None
        else:
            validate_path_characters(path, allow_root=True)
            self.path = path.removesuffix("/")
            self.item = self.get_item()
            self.item_type = "folder" if self.item and self.item.node_type == "folder" else "item"

        path_parts = [part for part in self.path.split("/") if part]
        self.breadcrumbs = ["/".join(path_parts[: i + 1]) for i in range(len(path_parts))]
        self._capabilities = compute_tree_capabilities(
            namespace,
            self.path,
            auth,
            referencing_config_path=referencing_config_path,
        )

    @property
    def is_visible(self) -> bool:
        return self._capabilities.is_visible

    @property
    def is_readable(self) -> bool:
        return self._capabilities.is_readable

    @property
    def is_writable(self) -> bool:
        return self._capabilities.is_writable

    @property
    def is_deletable(self) -> bool:
        return self._capabilities.is_deletable

    @property
    def is_movable(self) -> bool:
        return self._capabilities.is_movable

    @property
    def is_copyable(self) -> bool:
        return self._capabilities.is_copyable

    @property
    def is_creatable(self) -> bool:
        return self._capabilities.is_creatable

    @property
    def is_resolvable(self) -> bool:
        return self._capabilities.is_resolvable

    @property
    def is_folder_resolvable(self) -> bool:
        return self._capabilities.is_folder_resolvable

    @property
    def is_direct_resolve_target(self) -> bool:
        return self._capabilities.is_direct_resolve_target

    @property
    def is_extend_target(self) -> bool:
        return self._capabilities.is_extend_target

    @property
    def is_available_for_param(self) -> bool:
        return self._capabilities.is_available_for_param

    def _capabilities_for(self, path: str, *, referencing_config_path=None) -> TreeItemCapabilities:
        return compute_tree_capabilities(
            self.namespace,
            path,
            self.auth,
            referencing_config_path=referencing_config_path,
        )

    def _ensure_writable(self, *extra_paths: str) -> None:
        LockManager.ensure_paths_writable(self.namespace, [self.path, *extra_paths])

    def _filter_invisible_items(self, items):
        if self.auth is None:
            return items
        return [item for item in items if type(self).for_item(self.namespace, item, auth=self.auth).is_visible]

    def _ensure_visible(self) -> None:
        if self.item_type == "root":
            return
        if not self.is_visible:
            raise NotFound(f"Item wasn't found by path '{self.path}'")

    def _ensure_writable_capability(self) -> None:
        if not self.is_writable:
            raise CapabilityDenied(f"{self.item.node_type.title()} can't be updated by path '{self.path}'")

    def _ensure_movable(self, new_path: str) -> None:
        if not self.is_movable:
            raise CapabilityDenied(f"Built-in namespace item '{self.path}' cannot be moved")
        destination = new_path.strip("/")
        if not self._capabilities_for(destination).is_creatable:
            raise CapabilityDenied(f"Built-in namespace item '{destination}' cannot be a move target")

    def _ensure_copyable(self, new_path: str) -> None:
        if not self.is_copyable:
            raise CapabilityDenied(f"Built-in namespace item '{self.path}' cannot be copied")
        destination = new_path.strip("/")
        if not self._capabilities_for(destination).is_creatable:
            raise CapabilityDenied(f"Built-in namespace item '{destination}' cannot be a copy target")

    def _ensure_deletable(self) -> None:
        if not self.is_deletable:
            raise CapabilityDenied(f"Built-in namespace item '{self.path}' cannot be deleted")

    def _ensure_folder_children_capable(self, capability: str, *, action: str) -> None:
        attr = f"is_{capability}"
        for item in TreeMutateMixin._folder_content_items(self):
            if not getattr(self._capabilities_for(item.path), attr):
                raise CapabilityDenied(f"Built-in namespace item '{item.path}' cannot be {action}")

    def _actor_identity(self) -> str:
        return AuthManager.resolve_actor_identity(self.auth)

    def get_item(self, node_type=None):
        extra_filters = {}
        if node_type:
            extra_filters["node_type"] = node_type
        try:
            item = TreeItem.objects.get(namespace=self.namespace, path=self.path, **extra_filters)
            return getattr(item, item.node_type, item)
        except TreeItem.DoesNotExist:
            return None

    def get_or_raise(self, desired_item_type=None):
        if self.item is None:
            self.item = self.get_item()
            if self.item:
                self.item_type = "folder" if self.item.node_type == "folder" else "item"
        if self.item is None:
            raise NotFound(f"Item wasn't found by path '{self.path}'")

        if not desired_item_type:
            return self.item

        desired_item_type = [desired_item_type] if isinstance(desired_item_type, str) else desired_item_type
        if self.item.node_type in desired_item_type:
            return self.item

        desired_item_type_titles = " or ".join(dit.title() for dit in desired_item_type)
        raise TreeItem.DoesNotExist(f"{desired_item_type_titles} wasn't found by path '{self.path}' ")

    def _cast_to_specific(self, item):
        """Helper to return the actual subclass instance with child_count preserved."""
        specific = getattr(item, item.node_type, item)
        return specific

    @staticmethod
    def resolve_version(item, version_ref: str):
        """Resolve a tag name or numeric version string to a version row."""
        version_number = item.tags.get(version_ref)
        if version_number is None:
            if str(version_ref).isdigit() and int(version_ref) > 0:
                version_number = int(version_ref)
        if version_number is None:
            raise VersionNotFound(f"Tag/version {version_ref!r} not found on {item.path}")
        version_obj = item.versions.filter(
            version=version_number,
            deleted_at__isnull=True,
        ).first()
        if version_obj is None:
            raise VersionNotFound(f"Version {version_number} not found on {item.path}")
        return version_obj

    def version_resolvable(self, version_ref: str) -> bool:
        """Return whether ``resolve_version`` would succeed for ``item``."""
        try:
            self.resolve_version(self.item, version_ref)
            return True
        except VersionNotFound:
            return False
