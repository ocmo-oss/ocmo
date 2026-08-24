from django.db import models
from django.utils import timezone


class TreeLock(models.Model):
    """Subtree write freeze at a single tree path within a namespace."""

    namespace = models.ForeignKey(
        "core.Namespace",
        on_delete=models.CASCADE,
        related_name="tree_locks",
    )
    path = models.CharField(max_length=4096)
    reason = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.CharField(max_length=512, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("namespace", "path")]
        indexes = [
            models.Index(fields=["namespace", "path"]),
            models.Index(fields=["namespace", "expires_at"]),
        ]
        ordering = ["path"]

    def __str__(self):
        return f"{self.namespace.name}::lock::{self.path}"

    @property
    def is_active(self) -> bool:
        if self.expires_at is None:
            return True
        return self.expires_at > timezone.now()
