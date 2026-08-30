from ._common import *


class TreeCreateMixin:
    @webhook(
        lambda self, result, bound: (
            "config.created" if bound.get("node_type") in ("config", "template") else "resolver.created"
        ),
        version=lambda self, result, bound: result.tags.get("latest") if hasattr(result, "tags") else None,
    )
    @audit(
        lambda self, data, node_type: node_type,
        operation=OP_CREATE_ITEM,
    )
    @require_permissions(PermCheck(lambda self, node_type: f"{node_type}:write"))
    def create_item(self, data: str, node_type: str, *, validate_references: bool = True):
        if not self.is_creatable:
            raise CapabilityDenied(f"{node_type.title()} can't be created by path '{self.path}'")
        self._ensure_writable()
        if node_type == "folder":
            raise FolderCannotBeExplicitlyCreated(
                "Folder can't be explicitly created. They are generated on the fly when real tree items are created"
            )
        model_class = globals().get(node_type.title())
        if self.item:
            raise TreeItemConflict("Another item by the same path already exists")
        self._validate_path_conflicts()

        name = self.path.split("/")[-1]
        version_data = None
        description = ""
        if node_type in ("config", "template"):
            version_data = data
            item_data = {"tags": {"latest": 1}}
        elif node_type == "resolver":
            item_data = {
                "configuration": data or "",
            }
        else:
            item_data = {}

        resolver_plaintext_token = None
        if node_type == "resolver":
            resolver_plaintext_token = generate_resolver_token()

        actor = self._actor_identity()
        with transaction.atomic():
            parents = self._make_sure_path_exists()
            item = model_class(
                namespace=self.namespace,
                path=self.path,
                name=name,
                node_type=node_type,
                author=actor,
                description=description,
                parent=parents[-1] if parents else None,
                **item_data,
            )
            item.save()

            if node_type == "resolver" and resolver_plaintext_token:
                ResolverTokenManager(plaintext=resolver_plaintext_token).assign_to(item, 1)
                item.save(update_fields=["token1", "token1_lookup"])
                item._reveal_plaintext_token1 = resolver_plaintext_token

            if version_data:
                if node_type == "config":
                    self._validate_config_on_save(version_data, validate_references=validate_references)
                version_model_class = globals().get(f"{node_type.title()}Version")
                item_version = version_model_class(config=item, data=version_data, updater=actor)
                item_version.save()

        if node_type in ("config", "template"):
            enrich_audit(object_version=1)
        return item
