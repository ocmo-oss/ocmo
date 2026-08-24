import uuid

from django.db import models


class GlobalPermissionRule(models.Model):
    """
    Ordered list of Global Permission rules for namespace-object access control.

    Rules are evaluated in ascending position order; first matching rule wins.
    Only global administrators (OIDC_GLOBAL_ADMIN_CLAIM/VALUE) may manage these.
    These govern only namespace-object operations (list/get/create/update/delete
    namespace), NOT in-tree access which is governed by each namespace's _permissions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    position = models.FloatField(db_index=True)
    rule = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        rule_id = self.rule.get("id", str(self.id))
        return f"GlobalPermissionRule({rule_id}) @ {self.position}"
