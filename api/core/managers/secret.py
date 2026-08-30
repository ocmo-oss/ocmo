import logging

from django.db import transaction

from ..decorators import PermCheck, audit, enrich_audit, require_permissions, webhook
from ..exceptions import NotFound, SecretParameterError, TreeItemConflict
from ..models import Secret, SecretVersion, TreeItem
from ..shortcuts import safe_yaml_load, validate_path_characters
from .auth import AuthManager
from .crypto import CryptoManager
from .lock import LockManager
from .tree import TreeManager
from .webhook import WebhookManager

logger = logging.getLogger(__name__)


class SecretManager:
    """
    Manages Secret tree items and their AES-256-GCM encrypted versions.

    All plaintext values are decrypted in-process only; they are never persisted
    or returned unless the caller explicitly sets reveal=True.
    """

    def __init__(self, namespace, path, secret_obj=None, *, auth):
        self.namespace = namespace
        validate_path_characters(path)
        self.path = path
        self._secret = secret_obj
        self.auth = auth

    def get_or_raise(self) -> Secret:
        if self._secret is not None:
            return self._secret
        try:
            self._secret = TreeManager(self.namespace, self.path, auth=None).get_or_raise(["secret"])
        except (TreeItem.DoesNotExist, NotFound) as exc:
            raise SecretParameterError(f"Secret {self.path!r} not found") from exc
        return self._secret

    def resolve_plaintext_at_version(self, version_ref: str) -> tuple[int, str]:
        """Return (version_number, plaintext) for the secret at this manager's path."""
        secret = self.get_or_raise()
        version_number = secret.tags.get(version_ref)
        if version_number is None and version_ref.isdigit():
            version_number = int(version_ref)
        if version_number is None:
            raise SecretParameterError(f"Secret {self.path}: version/tag {version_ref!r} not found")
        ver = secret.versions.filter(version=version_number).first()
        if ver is None or not ver.encrypted_data:
            raise SecretParameterError(f"Secret {self.path}@{version_number} not available")
        plaintext = CryptoManager(self.namespace).decrypt_secret(ver.encrypted_data)
        if plaintext is None:
            raise SecretParameterError(f"Secret {self.path}@{version_number} not available")
        return version_number, plaintext

    def _validate_yaml(self, data: str) -> None:
        try:
            safe_yaml_load(data)
        except Exception as e:
            raise ValueError(f"Secret payload is not valid YAML: {e}")

    @webhook("secret.created", version=lambda self, result, bound: 1)
    @audit("secret", operation="Create item", object_version=1)
    @require_permissions(PermCheck("secret:write"))
    def create(self, plaintext: str) -> Secret:
        self._validate_yaml(plaintext)
        LockManager.ensure_path_writable(self.namespace, self.path)
        tm = TreeManager(self.namespace, self.path, auth=None)
        if tm.item:
            raise TreeItemConflict("Another item already exists at this path")
        tm._validate_path_conflicts()

        crypto = CryptoManager(self.namespace)
        blob = crypto.encrypt_secret(plaintext)

        actor = AuthManager.resolve_actor_identity(self.auth)
        name = self.path.split("/")[-1]
        with transaction.atomic():
            parents = tm._make_sure_path_exists()
            secret = Secret(
                namespace=self.namespace,
                path=self.path,
                name=name,
                parent=parents[-1] if parents else None,
                node_type="secret",
                author=actor,
                description="",
                tags={"latest": 1},
            )
            secret.save()
            version = SecretVersion(secret=secret, encrypted_data=blob, updater=actor)
            version.save()

        return secret

    @webhook(
        "secret.updated",
        skip_when=lambda self, result, bound: getattr(self, "_new_version_num", None) is None,
        version=lambda self, result, bound: getattr(self, "_new_version_num", None),
    )
    @audit("secret", operation="Update item")
    @require_permissions(PermCheck("secret:write"))
    def update(self, plaintext: str) -> Secret:
        self._new_version_num = None
        self._validate_yaml(plaintext)
        LockManager.ensure_path_writable(self.namespace, self.path)
        tm = TreeManager(self.namespace, self.path, auth=None)
        secret = tm.get_or_raise(["secret"])

        crypto = CryptoManager(self.namespace)
        latest_ver = secret.versions.order_by("-version").first()
        if latest_ver and latest_ver.encrypted_data:
            current_plaintext = crypto.decrypt_secret(latest_ver.encrypted_data)
            if current_plaintext == plaintext:
                return secret

        actor = AuthManager.resolve_actor_identity(self.auth)
        blob = crypto.encrypt_secret(plaintext)
        with transaction.atomic():
            version = SecretVersion(secret=secret, encrypted_data=blob, updater=actor)
            version.save()
            secret.tags["latest"] = version.version
            secret.save()

        self._new_version_num = version.version
        enrich_audit(object_version=version.version)
        WebhookManager.invalidate(self.namespace.id, secret_path=self.path)
        return secret

    def decrypt_version(self, secret, version_ref: str = "latest") -> tuple[int, str | None]:
        """Return (version_number, plaintext) for a secret version."""
        version_obj = TreeManager.resolve_version(secret, version_ref)
        crypto = CryptoManager(self.namespace)
        return version_obj.version, crypto.decrypt_secret(version_obj.encrypted_data)

    def attach_decrypted(self, version_ref: str = "latest") -> None:
        """
        Decrypt the requested version and attach the plaintext to each SecretVersion
        as _decrypted_data so that SecretSchemaExtended can include it in the response.
        """
        if self._secret is None:
            raise ValueError("SecretManager requires a secret_obj to attach_decrypted")

        version_obj = TreeManager.resolve_version(self._secret, version_ref)
        version_obj._decrypted_data = CryptoManager(self.namespace).decrypt_secret(version_obj.encrypted_data)
