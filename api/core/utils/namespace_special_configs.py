"""Bootstrap builtin configs and secrets for a new namespace."""

from __future__ import annotations

import secrets
from pathlib import Path

from ..managers.secret import SecretManager
from ..managers.tree import TreeManager
from ..managers.tree_capabilities import BUILTIN_NAMESPACE_SECRET_PATHS
from ..models import Namespace
from ..models.tree import TreeItem
from .permissions_schema_document import permissions_schema_yaml

_BUILTIN_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "data" / "builtin_schemas"
_BUILTIN_SCHEMA_PATHS = (
    "_permissions.schema",
    "_webhooks.schema",
    "_git_sync.schema",
)
_PERMISSIONS_WEBHOOKS_SCHEMA_PATHS = (
    "_permissions.schema",
    "_webhooks.schema",
)

_INITIAL_WEBHOOKS = """\
_ocmo:
  parameters:
    hmac_signing_key:
      type: secret
      value: _webhooks_secret@latest
      description: Default HMAC signing key for webhook payloads
webhooks:
  - id: example
    enabled: false
    url: https://example.com/ocmo/webhook
    events:
      - config.updated
      - config.tagged
    filter:
      paths:
        - project/**
    signature_key: "{!hmac_signing_key}"
    payload:
      preset: ocmo
"""


def _load_builtin_schema_content(path: str) -> str:
    if path == "_permissions.schema":
        return permissions_schema_yaml()
    return (_BUILTIN_SCHEMA_DIR / f"{path}.yaml").read_text(encoding="utf-8")


def sync_permissions_webhooks_schema_configs(namespace: Namespace) -> list[str]:
    """
    Replace ``_permissions.schema`` and ``_webhooks.schema`` with packaged YAML.

    Creates missing schema configs. Returns paths that were created or versioned.
    """
    updated: list[str] = []
    for schema_path in _PERMISSIONS_WEBHOOKS_SCHEMA_PATHS:
        content = _load_builtin_schema_content(schema_path)
        mgr = TreeManager(namespace, schema_path, auth=None)
        try:
            mgr.get_or_raise(["config"])
        except TreeItem.DoesNotExist:
            mgr.create_item(content, "config")
            updated.append(schema_path)
            continue

        assert mgr.item is not None
        latest = mgr.item.versions.last()
        if latest is not None and latest.data == content:
            continue

        mgr.update_item(content)
        updated.append(schema_path)
    return updated


def init_namespace_special_configs(namespace: Namespace) -> None:
    """Auto-create _permissions, _webhooks, _git_sync configs and companion secrets."""

    initial_permissions = "policies: []"
    initial_git_sync = "enabled: false"
    placeholder_secret = "placeholder: true"
    webhooks_secret = secrets.token_urlsafe(32)

    for schema_path in _BUILTIN_SCHEMA_PATHS:
        TreeManager(namespace, schema_path, auth=None).create_item(
            _load_builtin_schema_content(schema_path),
            "config",
        )

    for secret_path in BUILTIN_NAMESPACE_SECRET_PATHS:
        initial = webhooks_secret if secret_path == "_webhooks_secret" else placeholder_secret
        SecretManager(namespace, secret_path, auth=None).create(initial)

    for path, data in (
        ("_permissions", initial_permissions),
        ("_webhooks", _INITIAL_WEBHOOKS),
        ("_git_sync", initial_git_sync),
    ):
        TreeManager(namespace, path, auth=None).create_item(data, "config")
