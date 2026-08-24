from django.db import transaction
from django.db.utils import IntegrityError

from ..constants.audit_operations import (
    OP_CREATE_NAMESPACE,
    OP_DELETE_NAMESPACE,
    OP_READ_NAMESPACE,
    OP_UPDATE_NAMESPACE,
)
from ..decorators import PermCheck, audit, require_permissions, webhook
from ..exceptions import NamespaceActiveTagNotFound, NamespaceConflict
from ..models import Config, Namespace
from .webhook import WebhookManager

_NAMESPACE_CONFIG_ACTIVE_TAG_FIELDS = {
    "_permissions": "permissions_tag",
    "_webhooks": "webhooks_tag",
    "_git_sync": "git_sync_tag",
}

_NAMESPACE_TAG_FIELD_TO_CONFIG_PATH = {field: path for path, field in _NAMESPACE_CONFIG_ACTIVE_TAG_FIELDS.items()}


class NamespaceManager:
    def __init__(self, ns_name, *, auth):
        self.ns_name = ns_name
        self.auth = auth
        self.ns = self._load()

    def _validate_config_tag_exists(self, tag_field: str, tag_name: str) -> None:
        """Ensure tag_name is present on the namespace configuration config for tag_field."""
        config_path = _NAMESPACE_TAG_FIELD_TO_CONFIG_PATH.get(tag_field)
        if not config_path:
            return
        try:
            config = Config.objects.get(namespace=self.ns, path=config_path)
        except Config.DoesNotExist:
            raise NamespaceActiveTagNotFound(f"Namespace configuration config '{config_path}' was not found")
        if tag_name not in config.tags:
            raise NamespaceActiveTagNotFound(f"Tag '{tag_name}' does not exist on config '{config_path}'")

    def _load(self):
        if not self.ns_name:
            return None
        try:
            return Namespace.objects.get(name__iexact=self.ns_name)
        except Namespace.DoesNotExist:
            return None

    def exists(self):
        return self.ns is not None

    @classmethod
    def pk_exists(cls, pk: int) -> bool:
        return Namespace.objects.filter(pk=pk).exists()

    @classmethod
    def get_by_pk(cls, pk: int) -> Namespace:
        """Return namespace by primary key (raises Namespace.DoesNotExist)."""
        return Namespace.objects.get(pk=pk)

    @audit("namespace", object_id_attr="ns_name", operation=OP_READ_NAMESPACE)
    @require_permissions(
        PermCheck(
            "namespace:read",
            resource="ns_name",
            mask_as_not_found=True,
            not_found_message=lambda self: f"Namespace '{self.ns_name}' not found",
        ),
    )
    def get_or_raise(self):
        if self.ns:
            return self.ns
        raise Namespace.DoesNotExist(f"Namespace '{self.ns_name}' not found")

    def list(self, name_filter=None):
        qs = Namespace.objects.all()
        if name_filter:
            qs = qs.filter(name__icontains=name_filter)
        if self.auth is not None:
            pm = self.auth.permissions()
            return [ns for ns in qs if pm.check_namespace_object(ns.name, "read")]
        return qs

    @audit("namespace", object_id_attr="ns_name", operation=OP_CREATE_NAMESPACE)
    @require_permissions(PermCheck("namespace:write", resource="ns_name"))
    def create(self, payload) -> Namespace:
        from ..utils.namespace_special_configs import init_namespace_special_configs

        try:
            with transaction.atomic():
                ns = Namespace(
                    name=payload.name,
                    description=payload.description,
                )
                ns.full_clean()
                ns.save()
                self.ns = ns
                self.ns_name = ns.name
                init_namespace_special_configs(ns)
                return ns
        except IntegrityError:
            raise NamespaceConflict("Namespace with this name already exists")

    @webhook("namespace.updated", path=None, namespace_attribute="ns")
    @audit("namespace", object_id_attr="ns_name", operation=OP_UPDATE_NAMESPACE)
    @require_permissions(PermCheck("namespace:write", resource="ns_name"))
    def update(self, payload) -> Namespace:
        if self.ns is None:
            raise Namespace.DoesNotExist(f"Namespace '{self.ns_name}' not found")
        invalidate_webhooks = "webhooks_tag" in payload.model_fields_set
        for field in payload.model_fields_set:
            if field in _NAMESPACE_TAG_FIELD_TO_CONFIG_PATH:
                self._validate_config_tag_exists(field, getattr(payload, field))
            if hasattr(self.ns, field):
                setattr(self.ns, field, getattr(payload, field))
        try:
            self.ns.save()
        except IntegrityError:
            raise NamespaceConflict("Namespace with this name already exists")
        if invalidate_webhooks:
            WebhookManager.invalidate(self.ns.id)
        return self.ns

    @audit("namespace", object_id_attr="ns_name", operation=OP_DELETE_NAMESPACE)
    @require_permissions(PermCheck("namespace:delete", resource="ns_name"))
    def delete(self) -> dict:
        if self.ns is None:
            raise Namespace.DoesNotExist(f"Namespace '{self.ns_name}' not found")
        name = self.ns.name
        self.ns.delete()
        return {"success": True, "namespace": name}
