from datetime import datetime
from uuid import UUID

from ninja import Schema
from pydantic import Field


class AuditEventSchema(Schema):
    id: UUID
    occurred_at: datetime
    client_ip: str | None = None
    user_agent: str | None = None
    auth_id: str
    auth_email: str | None = None
    auth_type: str
    token_number: int | None = None
    namespace: str | None = Field(None, description="Denormalized namespace name")
    http_method: str
    api_endpoint: str
    object_type: str | None = None
    object_id: str | None = None
    object_version: int | None = None
    operation: str | None = None
    subresource_type: str | None = None
    subresource: str | None = None
    permission_ok: bool | None = None
    error: str | None = None
    resolve_type: str | None = None
    from_cache: bool | None = None
    parent_event_id: UUID | None = None
    event_kind: str

    @staticmethod
    def resolve_namespace(obj, context):
        return obj.namespace_name or (obj.namespace.name if obj.namespace_id else None)


class ResolveStatsSchema(Schema):
    direct: int = 0
    nested: int = 0


class ResolveSeriesBucketSchema(Schema):
    start: datetime
    direct: int = 0
    nested: int = 0
    errors: int = 0


class ResolveSeriesSchema(Schema):
    bucket_seconds: int
    buckets: list[ResolveSeriesBucketSchema]


class AuditTimelineEntrySchema(Schema):
    id: UUID
    occurred_at: datetime
    message: str = Field(..., description="User-friendly timeline note for this event")
    operation: str | None = None
    object_type: str | None = None
    object_id: str | None = None
    object_version: int | None = None
    subresource_type: str | None = None
    subresource: str | None = None
    auth_id: str
    auth_email: str | None = None
    auth_type: str
    permission_ok: bool | None = None
    event_kind: str

    @staticmethod
    def resolve_message(obj, context):
        from ..managers.audit.timeline import format_timeline_note

        return format_timeline_note(obj)
