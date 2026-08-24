from datetime import datetime
from uuid import UUID

from ninja import Query, Router
from ninja.pagination import paginate

from ..managers.audit import AuditListFilters, AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..operation_ids import (
    GET_GLOBAL_AUDIT_EVENT,
    GET_NAMESPACE_AUDIT_EVENT,
    LIST_GLOBAL_AUDIT,
    LIST_NAMESPACE_AUDIT,
    NAMESPACE_AUDIT_RESOLVE_SERIES,
    NAMESPACE_AUDIT_TIMELINE,
)
from ..schemas import ErrorSchema
from ..schemas.audit import AuditEventSchema, AuditTimelineEntrySchema, ResolveSeriesSchema

router = Router()


@router.get(
    "/audit/",
    response=list[AuditEventSchema],
    tags=["Audit"],
    operation_id=LIST_GLOBAL_AUDIT,
)
@paginate
def list_global_audit(
    request,
    auth_id: str | None = None,
    auth_email: str | None = None,
    auth_type: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    http_method: str | None = None,
    api_endpoint: str | None = None,
    permission_ok: bool | None = None,
    resolve_type: str | None = None,
    from_cache: bool | None = None,
    event_kind: str | None = None,
    category: str | None = None,
    parent_event_id: UUID | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    token_number: int | None = None,
    object_version: int | None = None,
    operation: str | None = None,
    subresource_type: str | None = None,
    subresource: str | None = None,
    event_id: UUID | None = None,
    error: str | None = None,
    namespace: str | None = None,
    search: str | None = None,
    occurred_from: datetime | None = Query(None, alias="from"),
    occurred_to: datetime | None = Query(None, alias="to"),
):
    """Cross-namespace audit log (global admin only)."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    filters = AuditListFilters(
        auth_id=auth_id,
        auth_email=auth_email,
        auth_type=auth_type,
        object_type=object_type,
        object_id=object_id,
        http_method=http_method,
        api_endpoint=api_endpoint,
        permission_ok=permission_ok,
        resolve_type=resolve_type,
        from_cache=from_cache,
        event_kind=event_kind,
        category=category,
        parent_event_id=parent_event_id,
        client_ip=client_ip,
        user_agent=user_agent,
        token_number=token_number,
        object_version=object_version,
        operation=operation,
        subresource_type=subresource_type,
        subresource=subresource,
        event_id=event_id,
        error=error,
        namespace_name=namespace,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    return AuditManager(auth=auth).list(filters, search=search)


@router.get(
    "/audit/{event_id}",
    response={200: AuditEventSchema, 404: ErrorSchema},
    tags=["Audit"],
    operation_id=GET_GLOBAL_AUDIT_EVENT,
)
def get_global_audit_event(request, event_id: str):
    """Get a single audit event (global admin only)."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    return AuditManager(auth=auth).get(event_id)


@router.get(
    "/ns/{namespace}/~audit/",
    response={200: list[AuditEventSchema], 404: ErrorSchema},
    tags=["Audit"],
    operation_id=LIST_NAMESPACE_AUDIT,
)
@paginate
def list_namespace_audit(
    request,
    namespace: str,
    auth_id: str | None = None,
    auth_email: str | None = None,
    auth_type: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    http_method: str | None = None,
    api_endpoint: str | None = None,
    permission_ok: bool | None = None,
    resolve_type: str | None = None,
    from_cache: bool | None = None,
    event_kind: str | None = None,
    category: str | None = None,
    parent_event_id: UUID | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    token_number: int | None = None,
    object_version: int | None = None,
    operation: str | None = None,
    subresource_type: str | None = None,
    subresource: str | None = None,
    event_id: UUID | None = None,
    error: str | None = None,
    search: str | None = None,
    occurred_from: datetime | None = Query(None, alias="from"),
    occurred_to: datetime | None = Query(None, alias="to"),
):
    """Namespace-scoped audit log (requires namespace:audit or global admin)."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    filters = AuditListFilters(
        auth_id=auth_id,
        auth_email=auth_email,
        auth_type=auth_type,
        object_type=object_type,
        object_id=object_id,
        http_method=http_method,
        api_endpoint=api_endpoint,
        permission_ok=permission_ok,
        resolve_type=resolve_type,
        from_cache=from_cache,
        event_kind=event_kind,
        category=category,
        parent_event_id=parent_event_id,
        client_ip=client_ip,
        user_agent=user_agent,
        token_number=token_number,
        object_version=object_version,
        operation=operation,
        subresource_type=subresource_type,
        subresource=subresource,
        event_id=event_id,
        error=error,
        namespace_name=namespace,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    return AuditManager(auth=auth, namespace=ns).list(filters, search=search)


@router.get(
    "/ns/{namespace}/~audit/timeline/",
    response={200: list[AuditTimelineEntrySchema], 404: ErrorSchema},
    tags=["Audit"],
    operation_id=NAMESPACE_AUDIT_TIMELINE,
)
@paginate
def namespace_audit_timeline(
    request,
    namespace: str,
    object_id: str,
    object_type: str,
    search: str | None = None,
):
    """Item-scoped audit timeline (requires ``<object_type>:audit`` on ``object_id``)."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return AuditManager(auth=auth, namespace=ns).item_timeline(
        object_id,
        object_type,
        search=search,
    )


@router.get(
    "/ns/{namespace}/~audit/resolve-series/",
    response={200: ResolveSeriesSchema, 404: ErrorSchema},
    tags=["Audit"],
    operation_id=NAMESPACE_AUDIT_RESOLVE_SERIES,
)
def namespace_audit_resolve_series(
    request,
    namespace: str,
    object_id: str,
    object_type: str,
    occurred_from: datetime = Query(..., alias="from"),
    occurred_to: datetime = Query(..., alias="to"),
    bucket_seconds: int = Query(..., ge=1800),
):
    """Time-bucketed direct vs nested resolve counts for a tree object."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    buckets = AuditManager(auth=auth, namespace=ns).resolve_stats_series(
        object_id=object_id,
        object_type=object_type,
        since=occurred_from,
        until=occurred_to,
        bucket_seconds=bucket_seconds,
    )
    return {
        "bucket_seconds": bucket_seconds,
        "buckets": buckets,
    }


@router.get(
    "/ns/{namespace}/~audit/{event_id}",
    response={200: AuditEventSchema, 404: ErrorSchema},
    tags=["Audit"],
    operation_id=GET_NAMESPACE_AUDIT_EVENT,
)
def get_namespace_audit_event(request, namespace: str, event_id: str):
    """Get a single audit event within a namespace."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return AuditManager(auth=auth, namespace=ns).get(event_id)
