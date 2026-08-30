from ._common import *
from .config_ops import collect_ocmo_reference_paths
from .constants import _COPY_NODE_TYPES


class TreeMutateMixin:
    @staticmethod
    def _copy_destination_path(source_root: str, source_path: str, dest_root: str) -> str:
        """Map *source_path* under *source_root* to the parallel path under *dest_root*."""
        old_root = source_root.strip("/")
        normalized_source = source_path.strip("/")
        normalized_dest = dest_root.strip("/")
        if normalized_source == old_root:
            return normalized_dest
        prefix = f"{old_root}/"
        if not normalized_source.startswith(prefix):
            return normalized_source
        suffix = normalized_source[len(prefix) :]
        return f"{normalized_dest}/{suffix}"

    @staticmethod
    def _topological_sort_paths(nodes: list[str], prerequisites: dict[str, set[str]]) -> list[str]:
        """Return *nodes* in an order that satisfies *prerequisites* (values must exist first)."""
        node_set = set(nodes)
        in_degree = {node: len(prerequisites.get(node, set()) & node_set) for node in nodes}
        dependents: dict[str, set[str]] = {node: set() for node in nodes}
        for node, prereqs in prerequisites.items():
            for prereq in prereqs:
                if prereq in dependents:
                    dependents[prereq].add(node)

        ready = sorted(node for node in nodes if in_degree[node] == 0)
        ordered: list[str] = []
        while ready:
            node = ready.pop(0)
            ordered.append(node)
            for dependent in sorted(dependents[node]):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)
            ready.sort()

        if len(ordered) != len(nodes):
            raise ValidationError("Circular _ocmo reference detected among items being copied")
        return ordered

    def _order_copy_descendants(
        self,
        descendants: list,
        *,
        source_root: str,
        destination: str,
        tag_to_copy: str,
    ) -> list:
        dest_to_item = {self._copy_destination_path(source_root, el.path, destination): el for el in descendants}
        dest_paths = list(dest_to_item)
        copy_set = set(dest_paths)
        prerequisites: dict[str, set[str]] = {dest: set() for dest in dest_paths}

        for el in descendants:
            if el.node_type != "config":
                continue
            source_item = self._cast_to_specific(el)
            dest_path = self._copy_destination_path(source_root, source_item.path, destination)
            version_to_copy = source_item.tags.get(tag_to_copy)
            if version_to_copy is None:
                continue
            version_obj = source_item.versions.filter(version=version_to_copy).first()
            if version_obj is None:
                continue
            try:
                metadata, _ = ConfigValidationManager.parse_config_yaml_document(version_obj.data)
            except ValidationError:
                continue
            base_folder = "/".join(dest_path.split("/")[:-1])
            for node_type, ref_path, _version in collect_ocmo_reference_paths(metadata, base_folder=base_folder):
                if node_type not in _COPY_NODE_TYPES:
                    continue
                mapped_ref = self._copy_destination_path(source_root, ref_path, destination)
                if mapped_ref in copy_set and mapped_ref != dest_path:
                    prerequisites[dest_path].add(mapped_ref)

        ordered_paths = self._topological_sort_paths(dest_paths, prerequisites)
        return [dest_to_item[path] for path in ordered_paths]

    @staticmethod
    def _folder_content_items(manager, *, copy_targets_only: bool = False) -> list:
        """Return non-folder descendants when *manager* points at a folder."""
        if manager.item is None or manager.item.node_type != "folder":
            return []
        queryset = manager.item.treeitem_ptr.descendants(include_self=True).exclude(node_type="folder")
        if copy_targets_only:
            queryset = queryset.filter(node_type__in=_COPY_NODE_TYPES)
        return list(queryset)

    @staticmethod
    def _folder_action_checks(manager, verb: str, *, copy_targets_only: bool = False) -> list:
        return [
            (f"{item.node_type}:{verb}", item.path)
            for item in TreeMutateMixin._folder_content_items(manager, copy_targets_only=copy_targets_only)
        ]

    @staticmethod
    def _move_destination_write_permission(manager, new_path: str):
        new_path = new_path.strip("/")
        item = manager.get_or_raise()
        if item.node_type == "folder":
            old_path = manager.path
            return [
                (
                    f"{child.node_type}:write",
                    new_path + child.path[len(old_path) :],
                )
                for child in TreeMutateMixin._folder_content_items(manager)
            ]
        return f"{item.node_type}:write"

    @staticmethod
    def _copy_destination_write_permission(manager, new_path: str):
        new_path = new_path.strip("/")
        item = manager.get_or_raise()
        if item.node_type == "folder":
            source_root = manager.path.strip("/")
            return [
                (
                    f"{child.node_type}:write",
                    TreeMutateMixin._copy_destination_path(source_root, child.path, new_path),
                )
                for child in TreeMutateMixin._folder_content_items(manager, copy_targets_only=True)
            ]
        return f"{item.node_type}:write"

    def move_item(self, new_path, *, validate_references: bool = True):
        """Move an item or folder subtree to a new path."""
        handlers = {
            "config": self.move_config,
            "template": self.move_template,
            "folder": self.move_folder,
            "resolver": self.move_resolver,
            "secret": self.move_secret,
        }
        node_type = self.get_or_raise().node_type
        if node_type not in handlers:
            raise ValidationError(f"Cannot move {node_type!r}")
        return handlers[node_type](new_path, validate_references=validate_references)

    @audit("config", operation=OP_MOVE_ITEM, subresource_type="path")
    @require_permissions(
        PermCheck("config:read"),
        PermCheck("config:delete"),
        PermCheck(
            action="config:write",
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def move_config(self, new_path, *, validate_references: bool = True):
        self.get_or_raise(["config"])
        self._ensure_movable(new_path)
        return self._generic_move(new_path, validate_references=validate_references)

    @audit("template", operation=OP_MOVE_ITEM, subresource_type="path")
    @require_permissions(
        PermCheck("template:read"),
        PermCheck("template:delete"),
        PermCheck(
            action="template:write",
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def move_template(self, new_path, *, validate_references: bool = True):
        self.get_or_raise(["template"])
        self._ensure_movable(new_path)
        return self._generic_move(new_path, validate_references=validate_references)

    @audit("folder", operation=OP_MOVE_ITEM, subresource_type="path")
    @require_permissions(
        PermCheck(action=lambda self: TreeMutateMixin._folder_action_checks(self, "read")),
        PermCheck(action=lambda self: TreeMutateMixin._folder_action_checks(self, "delete")),
        PermCheck(
            action=lambda self, new_path: TreeMutateMixin._move_destination_write_permission(self, new_path),
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def move_folder(self, new_path, *, validate_references: bool = True):
        self.get_or_raise(["folder"])
        self._ensure_movable(new_path)
        self._ensure_folder_children_capable("movable", action="moved")
        LockManager.ensure_subtree_writable(self.namespace, self.path)
        return self._generic_move(new_path, validate_references=validate_references)

    @audit("resolver", operation=OP_MOVE_ITEM, subresource_type="path")
    @require_permissions(
        PermCheck("resolver:read"),
        PermCheck("resolver:delete"),
        PermCheck(
            action="resolver:write",
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def move_resolver(self, new_path, *, validate_references: bool = True):
        self.get_or_raise(["resolver"])
        self._ensure_movable(new_path)
        return self._generic_move(new_path, validate_references=validate_references)

    @audit("secret", operation=OP_MOVE_ITEM, subresource_type="path")
    @require_permissions(
        PermCheck("secret:read"),
        PermCheck("secret:delete"),
        PermCheck(
            action="secret:write",
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def move_secret(self, new_path, *, validate_references: bool = True):
        self.get_or_raise(["secret"])
        self._ensure_movable(new_path)
        return self._generic_move(new_path, validate_references=validate_references)

    def _validate_move_references(self, destination: str) -> None:
        """Ensure config ``_ocmo`` references would still resolve after a move."""
        source_root = self.path.strip("/")
        destination = destination.strip("/")
        item = self.get_or_raise()

        if item.node_type == "config":
            configs = [self._cast_to_specific(item)]
        elif item.node_type == "folder":
            configs = [
                self._cast_to_specific(el)
                for el in item.treeitem_ptr.descendants(include_self=False).filter(node_type="config")
            ]
        else:
            return

        if not configs:
            return

        old_to_new = {
            cfg.path.strip("/"): self._copy_destination_path(source_root, cfg.path, destination) for cfg in configs
        }
        new_to_old = {new: old for old, new in old_to_new.items()}

        def resolve_db_path(resolved: str) -> str:
            return new_to_old.get(resolved, resolved)

        for cfg in configs:
            old_path = cfg.path.strip("/")
            new_path = old_to_new[old_path]
            latest_version = cfg.tags.get("latest")
            if latest_version is None:
                continue
            version_obj = cfg.versions.filter(version=latest_version).first()
            if version_obj is None:
                continue
            try:
                metadata, body = ConfigValidationManager.parse_config_yaml_document(version_obj.data)
            except ValidationError:
                continue

            mgr = type(self)(self.namespace, cfg.path, auth=self.auth)
            mgr.item = cfg
            ref_metadata = mgr._metadata_for_reference_validation(metadata, body, config_path=new_path)
            mgr._validate_config_ocmo_references(
                ref_metadata,
                config_path=new_path,
                resolve_db_path=resolve_db_path,
            )

    def _generic_move(self, new_path, *, validate_references: bool = True):
        destination = new_path.strip("/")
        enrich_audit(subresource=destination)
        self._ensure_writable(destination)
        old_path = self.path.strip("/")
        if destination == old_path:
            raise WrongMoveTargetException("Target path already match source item path")

        if destination.startswith(f"{old_path}/"):
            raise WrongMoveTargetException("It is not possible to move folder into itself")

        if validate_references:
            self._validate_move_references(destination)

        old_parent = self.item.treeitem_ptr.parent
        self.path = new_path.strip("/")
        path_parts = self.path.split("/")
        self.breadcrumbs = ["/".join(path_parts[: i + 1]) for i in range(len(path_parts))]
        self._validate_path_conflicts()

        if self.item_type == "item":
            with transaction.atomic():
                parents = self._make_sure_path_exists()
                self.item.parent = parents[-1] if parents else None
                self.item.path = self.path
                self.item.name = self.path.strip("/").split("/")[-1]
                self.item.save()
        else:
            with transaction.atomic():
                descendants = self.item.treeitem_ptr.descendants()

                parents = self._make_sure_path_exists()

                self.item.parent = parents[-1] if parents else None
                self.item.path = self.path
                self.item.name = self.path.strip("/").split("/")[-1]
                self.item.save()

                for desc in descendants:
                    relative_subpath = desc.path[len(old_path) :]
                    desc.path = destination + relative_subpath
                    desc.name = desc.path.strip("/").split("/")[-1]
                    desc.save()

        parent = old_parent
        while parent:
            if not parent.children.exists():
                next_parent = parent.parent
                parent.delete()
                parent = next_parent
            else:
                break

        return self.item

    def copy_item(self, new_path, tag_to_copy="latest", *, validate_references: bool = True):
        """Copy an item or subtree. Only the version at tag_to_copy is copied."""
        handlers = {
            "config": self.copy_config,
            "template": self.copy_template,
            "folder": self.copy_folder,
            "resolver": self.copy_resolver,
        }
        node_type = self.get_or_raise().node_type
        if node_type not in handlers:
            raise ValidationError(f"Cannot copy {node_type!r}")
        return handlers[node_type](new_path, tag_to_copy=tag_to_copy, validate_references=validate_references)

    @audit("config", operation=OP_COPY_ITEM)
    @require_permissions(
        PermCheck("config:read"),
        PermCheck(
            action="config:write",
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def copy_config(self, new_path, tag_to_copy="latest", *, validate_references: bool = True):
        self.get_or_raise(["config"])
        self._ensure_copyable(new_path)
        return self._generic_copy(new_path, tag_to_copy, validate_references=validate_references)

    @audit("template", operation=OP_COPY_ITEM)
    @require_permissions(
        PermCheck("template:read"),
        PermCheck(
            action="template:write",
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def copy_template(self, new_path, tag_to_copy="latest", *, validate_references: bool = True):
        self.get_or_raise(["template"])
        self._ensure_copyable(new_path)
        return self._generic_copy(new_path, tag_to_copy, validate_references=validate_references)

    @audit("folder", operation=OP_COPY_ITEM)
    @require_permissions(
        PermCheck(action=lambda self: TreeMutateMixin._folder_action_checks(self, "read")),
        PermCheck(
            action=lambda self, new_path: TreeMutateMixin._copy_destination_write_permission(self, new_path),
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def copy_folder(self, new_path, tag_to_copy="latest", *, validate_references: bool = True):
        self.get_or_raise(["folder"])
        self._ensure_copyable(new_path)
        self._ensure_folder_children_capable("copyable", action="copied")
        return self._generic_copy(new_path, tag_to_copy, validate_references=validate_references)

    @audit("resolver", operation=OP_COPY_ITEM)
    @require_permissions(
        PermCheck("resolver:read"),
        PermCheck(
            action="resolver:write",
            resource=arg("new_path", lambda p: p.strip("/")),
        ),
    )
    def copy_resolver(self, new_path, tag_to_copy="latest", *, validate_references: bool = True):
        self.get_or_raise(["resolver"])
        self._ensure_copyable(new_path)
        return self._generic_copy(new_path, tag_to_copy, validate_references=validate_references)

    def _generic_copy(self, new_path, tag_to_copy="latest", *, validate_references: bool = True):
        validate_tag_name(tag_to_copy)
        destination = new_path.strip("/")
        sr_type, sr_value = self.format_subresource(
            ["tag", "path"],
            [tag_to_copy, destination],
        )
        enrich_audit(subresource_type=sr_type, subresource=sr_value)
        self._ensure_writable(destination)
        if self.item.path == new_path:
            raise WrongMoveTargetException("Target path already match source item path")

        new_items = []

        source_root = self.path.strip("/")
        descendants = list(
            self.item.treeitem_ptr.descendants(include_self=True)
            .filter(node_type__in=["config", "template", "resolver"])
            .prefetch_related("config", "template", "resolver")
        )
        if validate_references:
            descendants = self._order_copy_descendants(
                descendants,
                source_root=source_root,
                destination=destination,
                tag_to_copy=tag_to_copy,
            )
        with transaction.atomic():
            for el in descendants:
                source_item = self._cast_to_specific(el)
                if source_item.node_type == "resolver":
                    configuration = source_item.configuration
                    if isinstance(configuration, str):
                        doc_data = configuration
                    else:
                        doc_data = json.dumps(configuration, sort_keys=True, separators=(",", ":"))
                    doc_data = doc_data or ""
                else:
                    version_to_copy = source_item.tags.get(tag_to_copy)
                    if version_to_copy is None:
                        raise VersionNotFound(
                            f"{source_item.node_type.title()} by path {source_item.path} "
                            f"doesn't have tag '{tag_to_copy}'. Can't copy"
                        )
                    doc_data = source_item.versions.filter(version=version_to_copy).first().data
                dest_path = self._copy_destination_path(source_root, source_item.path, destination)
                self.__class__(self.namespace, dest_path, auth=None)._ensure_writable()
                self.__class__(self.namespace, dest_path, auth=self.auth).create_item(
                    doc_data,
                    source_item.node_type,
                    validate_references=validate_references,
                )
                new_items.append(dest_path)
        return {"created": new_items}

    def delete_item(self, preview: bool, version: Optional[str] = None):
        """Delete a tree item, folder subtree, or a single version."""
        handlers = {
            "config": self.delete_config,
            "template": self.delete_template,
            "secret": self.delete_secret,
            "folder": self.delete_folder,
            "resolver": self.delete_resolver,
        }
        node_type = self.get_or_raise().node_type
        if node_type not in handlers:
            raise ValidationError(f"Cannot delete {node_type!r}")
        return handlers[node_type](preview=preview, version=version)

    @webhook(
        "config.deleted",
        skip_when=lambda self, result, bound: bound.get("preview", True),
    )
    @audit("config", operation=OP_DELETE_ITEM, skip_when=lambda self, preview, **_: preview)
    @require_permissions(PermCheck("config:delete"))
    def delete_config(self, preview: bool, version: Optional[str] = None):
        self.get_or_raise(["config"])
        self._ensure_deletable()
        return self._generic_delete(preview, version)

    @webhook(
        "config.deleted",
        skip_when=lambda self, result, bound: bound.get("preview", True),
    )
    @audit("template", operation=OP_DELETE_ITEM, skip_when=lambda self, preview, **_: preview)
    @require_permissions(PermCheck("template:delete"))
    def delete_template(self, preview: bool, version: Optional[str] = None):
        self.get_or_raise(["template"])
        self._ensure_deletable()
        return self._generic_delete(preview, version)

    @webhook(
        "secret.deleted",
        skip_when=lambda self, result, bound: bound.get("preview", True),
    )
    @audit("secret", operation=OP_DELETE_ITEM, skip_when=lambda self, preview, **_: preview)
    @require_permissions(PermCheck("secret:delete"))
    def delete_secret(self, preview: bool, version: Optional[str] = None):
        self.get_or_raise(["secret"])
        self._ensure_deletable()
        return self._generic_delete(preview, version)

    @audit("folder", operation=OP_DELETE_ITEM, skip_when=lambda self, preview, **_: preview)
    @require_permissions(PermCheck(action=lambda self: TreeMutateMixin._folder_action_checks(self, "delete")))
    def delete_folder(self, preview: bool, version: Optional[str] = None):
        self.get_or_raise(["folder"])
        self._ensure_deletable()
        self._ensure_folder_children_capable("deletable", action="deleted")
        return self._generic_delete(preview, version)

    @audit("resolver", operation=OP_DELETE_ITEM, skip_when=lambda self, preview, **_: preview)
    @require_permissions(PermCheck("resolver:delete"))
    def delete_resolver(self, preview: bool, version: Optional[str] = None):
        self.get_or_raise(["resolver"])
        self._ensure_deletable()
        return self._generic_delete(preview, version)

    def _generic_delete(self, preview: bool, version: Optional[str] = None):
        version_number: Optional[int] = None
        if version is not None and str(version).strip() != "":
            version_number = self.resolve_version(self.item, str(version)).version
        enrich_audit(object_version=version_number)
        self._ensure_writable()

        parent = self.item.treeitem_ptr.parent
        current_pk = self.item.treeitem_ptr.pk
        delete_list = []
        with transaction.atomic():
            if self.item.node_type == "folder":
                descendants = self.item.treeitem_ptr.descendants(include_self=True)
                delete_list = [str(el) for el in descendants]
                if not preview:
                    descendants.delete()
            else:
                if version_number is not None:
                    item_version = self.item.versions.filter(version=version_number, deleted_at__isnull=True).first()
                    if not item_version:
                        raise VersionNotFound(
                            f"{self.item.node_type.title()} by path {self.item.path} doesn't have version {version!r}"
                        )
                    delete_list = [str(item_version)]
                    if not preview:
                        item_version.data = ""
                        item_version.deleted_at = timezone.now()
                        item_version.updater = self._actor_identity()
                        item_version.save()
                        if self.item.tags.get("latest") == version_number:
                            latest_not_deleted_version = (
                                self.item.versions.filter(deleted_at__isnull=True).order_by("-version").first()
                            )
                            if latest_not_deleted_version:
                                self.item.tags["latest"] = latest_not_deleted_version.version
                            else:
                                del self.item.tags["latest"]
                            self.item.save()
                else:
                    delete_list = [str(self.item)]
                    if not preview:
                        self.item.delete()
        # Prune empty ancestor folders only after removing a whole tree item.
        if version_number is not None:
            return {"delete": delete_list}
        while parent:
            if not parent.children.exclude(pk=current_pk).exists():
                delete_list.append(str(parent))
                current_pk = parent.pk
                next_parent = parent.parent
                if not preview:
                    parent.delete()
                parent = next_parent
            else:
                # Found a folder that still has content; stop ascending
                break

        return {"delete": delete_list}
