from ..namespace import _NAMESPACE_CONFIG_ACTIVE_TAG_FIELDS
from ._common import *
from .constants import _RESERVED_TAGS


class TreeTagsMixin:
    def _check_active_namespace_tag_deletion(self, item, tag_name: str) -> None:
        field = _NAMESPACE_CONFIG_ACTIVE_TAG_FIELDS.get(item.path)
        if field and item.node_type == "config" and getattr(self.namespace, field) == tag_name:
            raise ActiveTagCannotBeDeleted(
                f"Tag '{tag_name}' is the active namespace {field} and cannot be deleted. "
                f"Re-point the namespace via PATCH /api/v1/ns/{self.namespace.name} first."
            )

    def set_item_tag(self, payload):
        """Set or delete a tag on a config, template, or secret."""
        handlers = {
            "config": self.set_config_tag,
            "template": self.set_template_tag,
            "secret": self.set_secret_tag,
        }
        node_type = self.get_or_raise().node_type
        if node_type not in handlers:
            raise ValidationError(f"Cannot set tag on {node_type!r}")
        return handlers[node_type](payload)

    @webhook(
        "config.tagged",
        version=lambda self, result, bound: bound.get("payload").version,
        tag=lambda self, result, bound: bound.get("payload").tag,
    )
    @audit("config", subresource_type="tag")
    @require_permissions(PermCheck("config:tag"))
    def set_config_tag(self, payload):
        self._ensure_writable()
        item = self.get_or_raise(["config"])
        reserved = _RESERVED_TAGS["config"]
        if payload.tag in reserved:
            raise ReservedTagsCantBeSet(
                f"Reserved tag '{payload.tag}' cannot be set or deleted manually on config items"
            )
        if payload.version:
            if item.versions.filter(version=payload.version).exists():
                if payload.version == item.tags.get(payload.tag):
                    raise ConfigTagAlreadyPointsToDesiredVersion("Config tag already points to desired version")
                item.tags[payload.tag] = payload.version
                item.save()
                item._requested_version = payload.version
                propagation_result = self.propagation_handler(
                    payload.tag,
                    payload.version,
                )
                if propagation_result is not None:
                    item._propagation_result = propagation_result
            else:
                raise VersionNotFound(f"Config by path {item.path} doesn't have version '{payload.version}'")
        else:
            self._check_active_namespace_tag_deletion(item, payload.tag)
            if payload.tag not in item.tags:
                raise ConfigTagDoesntExists(f"Can't delete tag for Config by path {item.path} since it doesn't exist")
            del item.tags[payload.tag]
            item.save()
        operation = OP_SET_TAG if payload.version is not None else OP_DELETE_TAG
        enrich_audit(
            operation=operation,
            object_version=payload.version,
            subresource=payload.tag,
        )
        return item

    @webhook(
        "config.tagged",
        version=lambda self, result, bound: bound.get("payload").version,
        tag=lambda self, result, bound: bound.get("payload").tag,
    )
    @audit("template", subresource_type="tag")
    @require_permissions(PermCheck("template:tag"))
    def set_template_tag(self, payload):
        self._ensure_writable()
        item = self.get_or_raise(["template"])
        reserved = _RESERVED_TAGS["template"]
        if payload.tag in reserved:
            raise ReservedTagsCantBeSet(
                f"Reserved tag '{payload.tag}' cannot be set or deleted manually on template items"
            )
        if payload.version:
            if item.versions.filter(version=payload.version).exists():
                if payload.version == item.tags.get(payload.tag):
                    raise ConfigTagAlreadyPointsToDesiredVersion("Template tag already points to desired version")
                item.tags[payload.tag] = payload.version
                item.save()
                item._requested_version = payload.version
            else:
                raise VersionNotFound(f"Template by path {item.path} doesn't have version '{payload.version}'")
        else:
            if payload.tag not in item.tags:
                raise ConfigTagDoesntExists(f"Can't delete tag for Template by path {item.path} since it doesn't exist")
            del item.tags[payload.tag]
            item.save()
        operation = OP_SET_TAG if payload.version is not None else OP_DELETE_TAG
        enrich_audit(
            operation=operation,
            object_version=payload.version,
            subresource=payload.tag,
        )
        return item

    @webhook(
        "secret.tagged",
        version=lambda self, result, bound: bound.get("payload").version,
        tag=lambda self, result, bound: bound.get("payload").tag,
    )
    @audit("secret", subresource_type="tag")
    @require_permissions(PermCheck("secret:tag"))
    def set_secret_tag(self, payload):
        self._ensure_writable()
        item = self.get_or_raise(["secret"])
        reserved = _RESERVED_TAGS["secret"]
        if payload.tag in reserved:
            raise ReservedTagsCantBeSet(
                f"Reserved tag '{payload.tag}' cannot be set or deleted manually on secret items"
            )
        if payload.version:
            if item.versions.filter(version=payload.version).exists():
                if payload.version == item.tags.get(payload.tag):
                    raise ConfigTagAlreadyPointsToDesiredVersion("Secret tag already points to desired version")
                item.tags[payload.tag] = payload.version
                item.save()
                item._requested_version = payload.version
            else:
                raise VersionNotFound(f"Secret by path {item.path} doesn't have version '{payload.version}'")
        else:
            if payload.tag not in item.tags:
                raise ConfigTagDoesntExists(f"Can't delete tag for Secret by path {item.path} since it doesn't exist")
            del item.tags[payload.tag]
            item.save()
        operation = OP_SET_TAG if payload.version is not None else OP_DELETE_TAG
        enrich_audit(
            operation=operation,
            object_version=payload.version,
            subresource=payload.tag,
        )
        return item

    def delete_config_tag(self, tag: str):
        return self.set_item_tag(TagPayload(tag=tag, version=None))

    @audit(
        "config",
        operation=OP_PROMOTE_STABLE_TAG,
        subresource_type="tag",
        subresource="stable",
    )
    @require_permissions(PermCheck("config:write"))
    def promote_stable_tag(self, version: int) -> bool:
        """Advance reserved ``stable`` tag after a successful resolve. Config only."""
        self._ensure_writable()
        item = self.get_or_raise(["config"])
        enrich_audit(object_version=version)
        if item.tags.get("stable") == version:
            return False
        if not item.versions.filter(version=version, deleted_at__isnull=True).exists():
            raise VersionNotFound(f"Config by path {item.path} doesn't have version '{version}'")
        item.tags["stable"] = version
        item.save(update_fields=["tags"])
        self.propagation_handler("stable", version)
        return True
