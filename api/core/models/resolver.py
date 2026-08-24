from django.db import models

from .tree import TreeItem


class Resolver(TreeItem):
    """
    Resolver model - programmatic access points with token authentication.

    Enables automated systems to resolve configuration subtrees.
    Supports dual-token rotation for zero-downtime credential updates.
    """

    # Tokens stored encrypted; token*_lookup holds HMAC fingerprint for auth lookup.
    token1 = models.TextField(null=True, blank=True)
    token1_lookup = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    token1_last_used = models.DateTimeField(null=True, blank=True)
    token2 = models.TextField(null=True, blank=True)
    token2_lookup = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    token2_last_used = models.DateTimeField(null=True, blank=True)

    configuration = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.namespace.name}:: Resolver:: {self.path}"
