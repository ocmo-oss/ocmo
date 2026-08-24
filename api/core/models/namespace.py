from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower


class Namespace(models.Model):
    """
    Namespace model - logical container for configuration trees.

    Permissions, webhooks, and Git sync are stored in dedicated Configs inside
    the namespace tree (_permissions, _webhooks, _git_sync). The *_tag fields
    point to which version tag of each Config is currently active.

    encrypted_dek holds the per-namespace Data Encryption Key (DEK) wrapped by
    the application master key (OCMO_MASTER_KEY) for AES-256-GCM secret encryption.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                r"^[a-zA-Z0-9_-]+$",
                "Only alphanumeric characters, hyphens and underscores are allowed.",
            )
        ],
    )
    description = models.TextField(max_length=4096, default="", blank=True)
    permissions_tag = models.CharField(max_length=50, default="latest")
    webhooks_tag = models.CharField(max_length=50, default="latest")
    git_sync_tag = models.CharField(max_length=50, default="latest")
    # Wrapped DEK: base64-encoded (nonce || ciphertext || tag) produced by AES-256-GCM
    # with OCMO_MASTER_KEY. Null only before first secret is written (lazy init allowed).
    encrypted_dek = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("name"), name="%(app_label)s_%(class)s_unique_name_case_insensitive"),
        ]
