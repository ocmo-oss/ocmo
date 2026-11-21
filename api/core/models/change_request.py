from django.db import models
from django.db.models import Max

from .tree import TreeItem


class ChangeRequest(models.Model):
    STATUS_OPEN = "open"
    STATUS_REJECTED = "rejected"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_APPLIED = "applied"

    STATUS_CHOICES = [
        (STATUS_OPEN, "open"),
        (STATUS_REJECTED, "rejected"),
        (STATUS_WITHDRAWN, "withdrawn"),
        (STATUS_APPLIED, "applied"),
    ]

    tree_item = models.ForeignKey(TreeItem, on_delete=models.CASCADE, related_name="change_requests")
    number = models.PositiveIntegerField(editable=False)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    base_version = models.PositiveIntegerField()
    title = models.CharField(max_length=200, default="", blank=True)
    description = models.TextField(max_length=4096, default="", blank=True)
    # Config/template: plaintext YAML. Secret: encrypted blob (same format as SecretVersion).
    content = models.TextField(blank=True, default="")
    content_encrypted = models.BinaryField(null=True, blank=True)
    created_by = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    applied_version = models.PositiveIntegerField(null=True, blank=True)
    applied_by = models.CharField(max_length=512, null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(max_length=4096, default="", blank=True)
    rejected_by = models.CharField(max_length=512, null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tree_item", "number"], name="core_changerequest_item_number_uniq"),
        ]
        indexes = [
            models.Index(fields=["tree_item", "status"]),
            models.Index(fields=["created_by", "tree_item", "status"]),
        ]
        ordering = ["tree_item", "number"]

    def save(self, *args, **kwargs):
        if self.pk is None and not self.number:
            agg = ChangeRequest.objects.filter(tree_item=self.tree_item).aggregate(m=Max("number"))
            self.number = (agg["m"] or 0) + 1
        super().save(*args, **kwargs)


class ChangeRequestApproval(models.Model):
    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="approvals")
    approver = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["change_request", "approver"],
                name="core_changerequestapproval_unique_approver",
            ),
        ]


class ChangeRequestComment(models.Model):
    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="comments")
    author = models.CharField(max_length=512)
    body = models.TextField(max_length=8192)
    anchor = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["change_request", "created_at"]),
        ]
        ordering = ["created_at"]
