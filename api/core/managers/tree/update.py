from ._common import *


class TreeUpdateMixin:
    def _finalize_content_update(
        self,
        content_changed: bool,
        actor: str,
        *,
        invalidate_webhooks_on_change: bool = False,
    ):
        if content_changed:
            self.item.author = actor
        self.item.save()
        self._content_changed = content_changed
        if content_changed:
            audit_version = None
            tags = getattr(self.item, "tags", None)
            if isinstance(tags, dict):
                audit_version = tags.get("latest")
            enrich_audit(object_version=audit_version)
        if content_changed and invalidate_webhooks_on_change and self.path == "_webhooks":
            WebhookManager.invalidate(self.namespace.id)
        return self.item

    def _generic_update_versioned(
        self,
        data: str,
        *,
        version_model_class,
        validate_data: Callable[[str], None] | None = None,
        invalidate_webhooks_on_change: bool = False,
    ):
        self._ensure_writable_capability()
        self._ensure_writable()
        actor = self._actor_identity()
        content_changed = False
        with transaction.atomic():
            if data and data != self.item.versions.last().data:
                if validate_data:
                    validate_data(data)
                item_version = version_model_class(config=self.item, data=data, updater=actor)
                item_version.save()
                self.item.tags["latest"] = item_version.version
                content_changed = True
        return self._finalize_content_update(
            content_changed,
            actor,
            invalidate_webhooks_on_change=invalidate_webhooks_on_change,
        )

    @audit(
        lambda self: self.item.node_type if self.item else "folder",
        operation=OP_UPDATE_DESCRIPTION,
    )
    @require_permissions(PermCheck(action=lambda self: f"{self.item.node_type}:describe" if self.item else None))
    def set_description(self, description: str):
        """Set item description without creating a new version."""
        self._ensure_writable()
        item = self.get_or_raise()
        item.description = description
        item.author = self._actor_identity()
        item.save()
        return item

    def update_item(self, data: str):
        """Update an existing tree item and its subclass metadata."""
        handlers = {
            "config": self.update_configs,
            "template": self.update_templates,
            "resolver": self.update_resolvers,
        }
        node_type = self.get_or_raise().node_type
        if node_type not in handlers:
            raise ValidationError(f"Cannot update {node_type!r} via update_item")
        return handlers[node_type](data)

    @webhook(
        "config.updated",
        skip_when=lambda self, result, bound: not getattr(self, "_content_changed", False),
        version=lambda self, result, bound: result.tags.get("latest"),
    )
    @audit("config", operation=OP_UPDATE_ITEM)
    @require_permissions(PermCheck("config:write"))
    def update_configs(self, data: str):
        """Create a new config version when content changes."""
        self.get_or_raise(["config"])
        return self._generic_update_versioned(
            data,
            version_model_class=ConfigVersion,
            validate_data=self._validate_config_on_save,
            invalidate_webhooks_on_change=True,
        )

    @webhook(
        "config.updated",
        skip_when=lambda self, result, bound: not getattr(self, "_content_changed", False),
        version=lambda self, result, bound: result.tags.get("latest"),
    )
    @audit("template", operation=OP_UPDATE_ITEM)
    @require_permissions(PermCheck("template:write"))
    def update_templates(self, data: str):
        """Create a new template version when content changes."""
        self.get_or_raise(["template"])
        return self._generic_update_versioned(
            data,
            version_model_class=TemplateVersion,
        )

    @webhook(
        "resolver.updated",
        skip_when=lambda self, result, bound: not getattr(self, "_content_changed", False),
        version=lambda self, result, bound: result.tags.get("latest") if hasattr(result, "tags") else None,
    )
    @audit("resolver", operation=OP_UPDATE_ITEM)
    @require_permissions(PermCheck("resolver:write"))
    def update_resolvers(self, data: str):
        """Update resolver configuration when content changes."""
        self.get_or_raise(["resolver"])
        self._ensure_writable_capability()
        self._ensure_writable()

        actor = self._actor_identity()
        content_changed = False
        with transaction.atomic():
            if data:
                configuration = data or ""
                current = self.item.configuration
                if isinstance(current, str):
                    current_str = current
                else:
                    current_str = json.dumps(current, sort_keys=True, separators=(",", ":"))
                if configuration != current_str:
                    self.item.configuration = configuration
                    content_changed = True

        return self._finalize_content_update(content_changed, actor)
