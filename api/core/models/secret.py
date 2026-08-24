from django.db import models, transaction
from django.db.models import Max

from .tree import TreeItem


class Secret(TreeItem):
    """
    Secret model - encrypted tree item for sensitive data.

    Values are always encrypted at rest using AES-256-GCM with the namespace DEK.
    Content is never returned unless the caller explicitly requests reveal=true.
    """

    tags = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.namespace.name}:: Secret:: {self.path}"


class SecretVersion(models.Model):
    """
    Immutable encrypted version snapshot of a Secret.

    Stores (nonce || ciphertext || GCM-tag) as a binary blob. Plaintext is never
    persisted. Identical immutability rules as ConfigVersion apply.
    """

    secret = models.ForeignKey("Secret", on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField(editable=False)
    # AES-256-GCM: 12-byte nonce || ciphertext || 16-byte tag
    encrypted_data = models.BinaryField(null=True, blank=True)
    updater = models.TextField()
    updated_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("secret", "version")]
        indexes = [
            models.Index(fields=["secret", "version"]),
        ]
        ordering = ["secret", "version"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            original = type(self).objects.get(pk=self.pk)
            if original.deleted_at is not None:
                raise ValueError("Deleted Secret version cannot be updated.")
            if not (self.deleted_at and self.encrypted_data is None):
                raise ValueError("Secret version records are immutable. Create a new version instead.")
        else:
            with transaction.atomic():
                last_version = type(self).objects.filter(secret=self.secret).aggregate(max_v=Max("version"))["max_v"]
                self.version = (last_version or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.secret.namespace.name}:: Secret:: {self.secret.path}@{self.version}"
