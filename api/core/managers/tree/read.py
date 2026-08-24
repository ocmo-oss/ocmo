from ._common import *


class TreeReadMixin:
    def get_extended(self, version: str = "latest", reveal: bool = False):
        """Return tree item with optional version and decrypted secret data."""
        handlers = {
            "config": self.get_configs,
            "template": self.get_templates,
            "secret": self.get_secrets,
            "resolver": self._get_resolver,
            "folder": self._get_folder,
        }
        node_type = self.get_or_raise().node_type
        if node_type not in handlers:
            raise ValidationError(f"Extended get is not supported for node type {node_type!r}")
        return handlers[node_type](version=version, reveal=reveal)

    @audit("config")
    @require_permissions(PermCheck("config:read"))
    def get_configs(self, version: str = "latest", reveal: bool = False):
        """Return a config with version data."""
        item = self.get_or_raise(["config"])
        resolved_version = None
        if is_version_number_ref(version):
            resolved_version = int(version)
        else:
            try:
                resolved_version = self.resolve_version(item, version).version
            except Exception:
                resolved_version = None
        sr_type, sr_value = tag_subresource_from_ref(version) or (None, None)
        enrich_audit(
            operation=read_operation_for_type(item.node_type),
            object_version=resolved_version,
            subresource_type=sr_type,
            subresource=sr_value,
        )
        item._requested_version = version
        return item

    @audit("template")
    @require_permissions(PermCheck("template:read"))
    def get_templates(self, version: str = "latest", reveal: bool = False):
        """Return a template with version data."""
        item = self.get_or_raise(["template"])
        resolved_version = None
        if is_version_number_ref(version):
            resolved_version = int(version)
        else:
            try:
                resolved_version = self.resolve_version(item, version).version
            except Exception:
                resolved_version = None
        sr_type, sr_value = tag_subresource_from_ref(version) or (None, None)
        enrich_audit(
            operation=read_operation_for_type(item.node_type),
            object_version=resolved_version,
            subresource_type=sr_type,
            subresource=sr_value,
        )
        item._requested_version = version
        return item

    @audit("secret")
    @require_permissions(PermCheck("secret:read"))
    def get_secrets(self, version: str = "latest", reveal: bool = False):
        """Return a secret with version data and optional decrypted content."""
        item = self.get_or_raise(["secret"])
        resolved_version = None
        if reveal:
            version_obj = self.resolve_version(item, version)
            item._decrypted_plaintext = CryptoManager(self.namespace).decrypt_secret(version_obj.encrypted_data)
            resolved_version = version_obj.version
        elif is_version_number_ref(version):
            resolved_version = int(version)
        else:
            try:
                resolved_version = self.resolve_version(item, version).version
            except Exception:
                resolved_version = None
        sr_type, sr_value = tag_subresource_from_ref(version) or (None, None)
        enrich_audit(
            operation=read_operation_for_type(item.node_type),
            object_version=resolved_version,
            subresource_type=sr_type,
            subresource=sr_value,
        )
        item._requested_version = version
        return item

    @audit("resolver")
    @require_permissions(PermCheck("resolver:read"))
    def _get_resolver(self, version: str = "latest", reveal: bool = False):
        """Return a resolver item."""
        item = self.get_or_raise(["resolver"])
        resolved_version = None
        if is_version_number_ref(version):
            resolved_version = int(version)
        else:
            try:
                resolved_version = self.resolve_version(item, version).version
            except Exception:
                resolved_version = None
        sr_type, sr_value = tag_subresource_from_ref(version) or (None, None)
        enrich_audit(
            operation=read_operation_for_type(item.node_type),
            object_version=resolved_version,
            subresource_type=sr_type,
            subresource=sr_value,
        )
        return item

    @audit("folder")
    @require_permissions(PermCheck("folder:read"))
    def _get_folder(self, version: str = "latest", reveal: bool = False):
        """Return a folder item."""
        item = self.get_or_raise(["folder"])
        resolved_version = None
        if is_version_number_ref(version):
            resolved_version = int(version)
        else:
            try:
                resolved_version = self.resolve_version(item, version).version
            except Exception:
                resolved_version = None
        sr_type, sr_value = tag_subresource_from_ref(version) or (None, None)
        enrich_audit(
            operation=read_operation_for_type(item.node_type),
            object_version=resolved_version,
            subresource_type=sr_type,
            subresource=sr_value,
        )
        return item

    def _to_navigation_node(self, item) -> Optional[dict]:
        if item is None:
            return None
        specific = getattr(item, item.node_type, item)
        return {
            "name": specific.name,
            "path": specific.path,
            "node_type": specific.node_type,
        }

    @audit(
        "namespace",
        object_id_attr=lambda self: self.namespace.name,
        operation=OP_NAVIGATE,
    )
    @require_permissions(PermCheck("namespace:read", resource=lambda self: self.namespace.name))
    def navigate(self, recursive=False, include_self=True, *, limit=100, offset=0):
        """
        Generic traversal method.
        - If path is exact: returns item and its children.
        - If path is prefix: returns all items under that prefix.
        - ``limit``/``offset`` paginate the ``children`` list only.
        """

        if self.item_type != "root":
            self.get_or_raise()
            self._ensure_visible()

        response = {
            "item": self._to_navigation_node(self.item) if self.item else None,
            "children": [],
            "children_count": 0,
            "breadcrumbs": self.breadcrumbs,
            "is_leaf": self.item_type == "item",
        }

        if response["is_leaf"]:
            return response

        if recursive:
            children = (
                TreeItem.objects.filter(namespace=self.namespace)
                .select_related("config", "template", "resolver")
                .filter(path__startswith=f"{self.path}/" if self.path else "")
                .order_by("path")
            )
        else:
            if self.item:
                children = self.item.children.select_related("config", "template", "resolver").order_by("path")
            else:
                children = (
                    TreeItem.objects.filter(namespace=self.namespace, parent=None)
                    .select_related("config", "template", "resolver")
                    .order_by("path")
                )

        if self.auth is None:
            children_count = children.count()
            page = children[offset : offset + limit]
        else:
            visible = list(self._filter_invisible_items(children))
            children_count = len(visible)
            page = visible[offset : offset + limit]

        response["children_count"] = children_count
        response["children"] = [self._to_navigation_node(getattr(child, child.node_type, child)) for child in page]
        return response

    def get_tree(self, root_path=None):
        queryset = TreeItem.objects.filter(namespace=self.namespace).with_tree_fields()
        if root_path:
            root = TreeItem.objects.get(namespace=self.namespace, path=root_path)
            return queryset.descendants(root, include_self=True)
        return queryset

    def _build_search_queryset(self, query=None, node_types=None):
        """Return namespace search queryset ordered by path (no slice)."""
        if self.item_type != "root":
            self.get_or_raise()
            self._ensure_visible()

        # Start with base queryset in the correct namespace
        queryset = TreeItem.objects.filter(namespace=self.namespace).select_related("config", "template", "resolver")

        if self.auth and self.auth.is_resolver:
            scope = self.auth.access_scope
            if scope:
                queryset = queryset.filter(Q(path=scope) | Q(path__startswith=f"{scope}/"))

        # 1. Filter by Branch (Scope)
        if self.path:
            # Use the GiST index optimized startswith
            queryset = queryset.filter(path__startswith=self.path.strip("/") + "/")

        # 2. Filter by Item Type
        if node_types:
            # Matches against the node_type field in TreeItem
            queryset = queryset.filter(node_type__in=node_types)

        # 3. Text Search (Name or Path parts)
        if query:
            # icontains is standard; for massive trees, consider Postgres full-text search
            queryset = queryset.filter(Q(name__icontains=query) | Q(path__icontains=query))

        return queryset.order_by("path")

    @audit(
        "namespace",
        object_id_attr=lambda self: self.namespace.name,
        operation=OP_SEARCH,
    )
    @require_permissions(PermCheck("namespace:read", resource=lambda self: self.namespace.name))
    def search(self, query=None, node_types=None):
        """
        Search for items within a namespace.

        Returns a queryset when auth is absent (DB-level pagination). When auth
        is set, returns a list of navigation-node dicts with visibility applied
        (in-memory pagination via the API ``@paginate`` decorator).
        """
        if query:
            enrich_audit(subresource_type="query", subresource=query)
        queryset = self._build_search_queryset(query, node_types)
        if self.auth is None:
            return queryset
        return [
            self._to_navigation_node(self._cast_to_specific(item)) for item in self._filter_invisible_items(queryset)
        ]
