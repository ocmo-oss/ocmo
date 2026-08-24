import uuid

from django.db import models


class AuditEvent(models.Model):
    """Append-only audit log entry."""

    EVENT_KIND_OPERATION = "operation"
    EVENT_KIND_RESOLVE_REQUEST = "resolve_request"
    EVENT_KIND_RESOLVE_PARTICIPANT = "resolve_participant"

    EVENT_KIND_CHOICES = [
        (EVENT_KIND_OPERATION, "operation"),
        (EVENT_KIND_RESOLVE_REQUEST, "resolve_request"),
        (EVENT_KIND_RESOLVE_PARTICIPANT, "resolve_participant"),
    ]

    RESOLVE_TYPE_DIRECT = "direct"
    RESOLVE_TYPE_NESTED = "nested"

    RESOLVE_TYPE_CHOICES = [
        (RESOLVE_TYPE_DIRECT, "direct"),
        (RESOLVE_TYPE_NESTED, "nested"),
    ]

    AUTH_TYPE_USER = "user"
    AUTH_TYPE_RESOLVER = "resolver"

    AUTH_TYPE_CHOICES = [
        (AUTH_TYPE_USER, "user"),
        (AUTH_TYPE_RESOLVER, "resolver"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    client_ip = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    auth_id = models.CharField(max_length=512)
    auth_email = models.CharField(max_length=512, null=True, blank=True)
    auth_type = models.CharField(max_length=16, choices=AUTH_TYPE_CHOICES)
    token_number = models.PositiveSmallIntegerField(null=True, blank=True)

    namespace = models.ForeignKey(
        "Namespace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    namespace_name = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    http_method = models.CharField(max_length=16)
    api_endpoint = models.CharField(max_length=2048)

    object_type = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    object_id = models.CharField(max_length=2048, null=True, blank=True, db_index=True)
    object_version = models.PositiveIntegerField(null=True, blank=True)

    operation = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    subresource_type = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    subresource = models.CharField(max_length=2048, null=True, blank=True)

    permission_ok = models.BooleanField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)

    resolve_type = models.CharField(
        max_length=16,
        choices=RESOLVE_TYPE_CHOICES,
        null=True,
        blank=True,
        db_index=True,
    )
    from_cache = models.BooleanField(null=True, blank=True)

    parent_event = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participants",
    )

    event_kind = models.CharField(max_length=32, choices=EVENT_KIND_CHOICES, db_index=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["namespace", "occurred_at"]),
            models.Index(fields=["namespace_name", "occurred_at"]),
            models.Index(fields=["object_id", "resolve_type", "occurred_at"]),
            models.Index(fields=["auth_id"]),
        ]

    def __str__(self) -> str:
        return f"AuditEvent({self.event_kind} {self.object_type}:{self.object_id} @ {self.occurred_at})"
