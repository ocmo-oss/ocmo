"""AuditManager for append-only operation logging."""

from __future__ import annotations

import builtins
import contextvars
import logging
import math
import re
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils import timezone

from ...constants.audit_operations import (
    OP_MOVE_ITEM,
    OP_REFERENCED_IN_RESOLVE,
    OP_RESOLVE,
)
from ...decorators.audit import AuditEventContext, _audit_operation_context, _take_audit_context
from ...decorators.binding import bind_args, invoke, resolve_resource
from ...decorators.permissions import PermCheck, arg, require_permissions
from ...exceptions import NotFound, PermissionDenied
from ...models import AuditEvent, Namespace
from ...shortcuts import tag_subresource_from_ref
from ..auth import AuthManager
from .timeline import (
    format_timeline_note as format_timeline_note,
)
from .timeline import (
    infer_operation,
)
from .timeline import (
    read_operation_for_type as read_operation_for_type,
)

if TYPE_CHECKING:
    from ..resolving import CacheParticipant

logger = logging.getLogger(__name__)

AUDIT_MODE_ALL = "all"
AUDIT_MODE_MODIFICATIONS_AND_RESOLVE = "modifications-and-resolve"
AUDIT_MODE_RESOLVE = "resolve"
VALID_AUDIT_MODES = frozenset(
    {
        AUDIT_MODE_ALL,
        AUDIT_MODE_MODIFICATIONS_AND_RESOLVE,
        AUDIT_MODE_RESOLVE,
    }
)
MODIFICATION_HTTP_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_RESOLVE_EVENT_KINDS = frozenset(
    {
        AuditEvent.EVENT_KIND_RESOLVE_REQUEST,
        AuditEvent.EVENT_KIND_RESOLVE_PARTICIPANT,
    }
)

_request_audit: contextvars.ContextVar[AuditManager | None] = contextvars.ContextVar(
    "request_audit",
    default=None,
)


def client_ip_from_request(request) -> str | None:
    """Extract client IP from X-Forwarded-For or REMOTE_ADDR."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR")


@dataclass
class AuditEventDraft:
    """In-memory audit row under construction."""

    event_kind: str = AuditEvent.EVENT_KIND_OPERATION
    client_ip: str | None = None
    user_agent: str | None = None
    auth_id: str = ""
    auth_email: str | None = None
    auth_type: str = AuditEvent.AUTH_TYPE_USER
    token_number: int | None = None
    namespace: Any = None
    namespace_name: str | None = None
    http_method: str = ""
    api_endpoint: str = ""
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
    parent_event: AuditEvent | None = None


@dataclass
class AuditListFilters:
    """Optional filters for audit list queries."""

    auth_id: str | None = None
    auth_email: str | None = None
    auth_type: str | None = None
    object_type: str | None = None
    object_id: str | None = None
    http_method: str | None = None
    api_endpoint: str | None = None
    permission_ok: bool | None = None
    resolve_type: str | None = None
    from_cache: bool | None = None
    event_kind: str | None = None
    category: str | None = None
    parent_event_id: str | UUID | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    token_number: int | None = None
    object_version: int | None = None
    operation: str | None = None
    subresource_type: str | None = None
    subresource: str | None = None
    event_id: str | UUID | None = None
    error: str | None = None
    namespace_name: str | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None

    def __post_init__(self) -> None:
        if isinstance(self.parent_event_id, UUID):
            self.parent_event_id = str(self.parent_event_id)
        if isinstance(self.event_id, UUID):
            self.event_id = str(self.event_id)


@dataclass
class ResolveStats:
    direct: int = 0
    nested: int = 0


@dataclass
class ResolveSeriesBucket:
    start: datetime
    direct: int = 0
    nested: int = 0
    errors: int = 0


_audit_list_access = PermCheck(
    lambda self: "global:admin" if self.namespace is None else "namespace:audit",
    resource=lambda self: self.namespace.name if self.namespace is not None else "",
)

_item_audit_access = PermCheck(
    action=lambda self, object_id, object_type, **_: f"{object_type}:audit",
    resource=arg("object_id"),
    mask_as_not_found=True,
)


class AuditManager:
    """Build, persist, and query append-only audit events.

    One instance is bound per HTTP request via :meth:`bind` and retrieved
    elsewhere with :meth:`current`.
    """

    def __init__(
        self,
        auth: AuthManager | None = None,
        namespace=None,
        *,
        request=None,
    ) -> None:
        self.auth = auth
        self.namespace = namespace
        self.request = request
        self._draft: AuditEventDraft | None = None
        self._draft_stack: list[AuditEventDraft] = []
        self._last_saved: AuditEvent | None = None

    @classmethod
    def bind(cls, request, auth: AuthManager, namespace=None) -> AuditManager:
        """Create and store the request-scoped AuditManager singleton."""
        mgr = cls(auth=auth, namespace=namespace, request=request)
        _request_audit.set(mgr)
        return mgr

    @classmethod
    def unbind(cls) -> None:
        """Clear the request-scoped AuditManager (mainly for tests)."""
        current = _request_audit.get()
        if current is not None:
            current._draft = None
            current._draft_stack.clear()
        _request_audit.set(None)

    @classmethod
    def current(cls) -> AuditManager | None:
        """Return the request-scoped AuditManager, if bound."""
        return _request_audit.get()

    @classmethod
    def from_manager(cls, manager) -> AuditManager | None:
        """Return the bound singleton, updating namespace from *manager*."""
        audit_mgr = cls.current()
        if audit_mgr is None:
            return None

        namespace = getattr(manager, "namespace", None)
        if namespace is None and hasattr(manager, "ns") and manager.ns is not None:
            namespace = manager.ns
        if namespace is not None:
            audit_mgr.set_namespace(namespace)
        return audit_mgr

    @classmethod
    def for_decorated_call(
        cls,
        manager,
        *,
        auth_manager_attribute: str = "auth",
        skip_when_no_auth: bool = True,
    ) -> AuditManager | None:
        """Return request-scoped manager for a decorated call, or None to skip auditing."""
        if getattr(manager, auth_manager_attribute, None) is None:
            return None
        if cls.current() is None and skip_when_no_auth:
            return None
        return cls.from_manager(manager)

    def set_namespace(self, namespace) -> AuditManager:
        """Attach or replace the namespace context for subsequent events."""
        self.namespace = namespace
        if self._draft is not None and namespace is not None:
            self._draft.namespace = namespace
            self._draft.namespace_name = namespace.name
        return self

    def _prefill_actor_and_request(self) -> None:
        if self._draft is None:
            return

        auth = self.auth
        if auth is not None:
            self._draft.auth_id = str(auth.identifier or AuthManager.DEFAULT_ACTOR_IDENTITY)
            email = auth.email
            self._draft.auth_email = str(email) if email is not None else None
            self._draft.auth_type = AuditEvent.AUTH_TYPE_RESOLVER if auth.is_resolver else AuditEvent.AUTH_TYPE_USER
            self._draft.token_number = auth.token_number
        else:
            self._draft.auth_id = AuthManager.DEFAULT_ACTOR_IDENTITY
            self._draft.auth_type = AuditEvent.AUTH_TYPE_USER

        request = self.request
        if request is not None and hasattr(request, "META"):
            self._draft.http_method = getattr(request, "method", "") or ""
            self._draft.api_endpoint = getattr(request, "path", "") or ""
            self._draft.client_ip = client_ip_from_request(request)
            self._draft.user_agent = request.META.get("HTTP_USER_AGENT")

        if self._draft.namespace is None and self.namespace is not None:
            self._draft.namespace = self.namespace
            self._draft.namespace_name = self.namespace.name

    def begin(self, event_kind: str = AuditEvent.EVENT_KIND_OPERATION) -> AuditManager:
        if self._draft is not None:
            self._draft_stack.append(self._draft)
        self._draft = AuditEventDraft(event_kind=event_kind)
        self._prefill_actor_and_request()
        return self

    def set_object(
        self,
        object_type: str,
        object_id: str | None,
        *,
        version: int | None = None,
    ) -> AuditManager:
        if self._draft is None:
            raise RuntimeError("Call begin() before set_object()")
        self._draft.object_type = object_type
        self._draft.object_id = object_id
        self._draft.object_version = version
        if object_type == "namespace" and object_id and self._draft.namespace_name is None:
            self._draft.namespace_name = object_id
        return self

    def set_resolve(
        self,
        *,
        resolve_type: str | None = None,
        from_cache: bool | None = None,
    ) -> AuditManager:
        if self._draft is None:
            raise RuntimeError("Call begin() before set_resolve()")
        self._draft.resolve_type = resolve_type
        self._draft.from_cache = from_cache
        return self

    def set_outcome(
        self,
        *,
        permission_ok: bool | None,
        error: str | None = None,
    ) -> AuditManager:
        if self._draft is None:
            raise RuntimeError("Call begin() before set_outcome()")
        self._draft.permission_ok = permission_ok
        self._draft.error = error
        return self

    def set_parent(self, parent: AuditEvent) -> AuditManager:
        if self._draft is None:
            raise RuntimeError("Call begin() before set_parent()")
        self._draft.parent_event = parent
        return self

    def set_operation(self, operation: str | None) -> AuditManager:
        if self._draft is None:
            raise RuntimeError("Call begin() before set_operation()")
        self._draft.operation = operation
        return self

    def set_subresource(
        self,
        *,
        subresource_type: str | None = None,
        subresource: str | None = None,
    ) -> AuditManager:
        if self._draft is None:
            raise RuntimeError("Call begin() before set_subresource()")
        self._draft.subresource_type = subresource_type
        self._draft.subresource = subresource
        return self

    def begin_operation(self, object_type: str, object_id: str | None) -> AuditManager:
        return self.begin(AuditEvent.EVENT_KIND_OPERATION).set_object(object_type, object_id)

    @contextmanager
    def operation(
        self,
        object_type: str,
        object_id: str | None,
        *,
        resolve_type: str | None = None,
        operation: str | None = None,
    ):
        """Context manager for one audited manager operation."""
        self.begin_operation(object_type, object_id)
        if resolve_type:
            self.set_resolve(resolve_type=resolve_type)
        if operation:
            self.set_operation(operation)
        try:
            yield
        except PermissionDenied as exc:
            event = self._finalize_operation(permission_ok=False, error=str(exc))
            self._attach_audit_event_id(exc, event)
            raise
        except Exception as exc:
            event = self._finalize_operation(permission_ok=True, error=str(exc))
            self._attach_audit_event_id(exc, event)
            raise
        else:
            self._finalize_operation(permission_ok=True)

    @staticmethod
    def _attach_audit_event_id(exc: BaseException, event: AuditEvent | None) -> None:
        if event is not None:
            setattr(exc, "audit_event_id", event.id)

    def _finalize_operation(
        self,
        *,
        permission_ok: bool,
        error: str | None = None,
    ) -> AuditEvent | None:
        try:
            return self.set_outcome(permission_ok=permission_ok, error=error).save()
        except Exception:
            logger.exception("Failed to save audit event")
            return None

    @staticmethod
    def _resolve_post_value(spec, manager, bound_args: dict, result) -> Any:
        """Resolve a decorator field that may be a constant or post-call callable."""
        if spec is None:
            return None
        if not callable(spec):
            return spec
        try:
            return spec(manager, result, bound_args)
        except TypeError:
            return invoke(spec, manager, bound_args)

    @staticmethod
    def _merge_post_field_spec(
        body_ctx: AuditEventContext | None,
        attr: str,
        decorator_spec: str | Callable | int | None,
    ) -> str | Callable | int | None:
        if body_ctx is not None:
            value = getattr(body_ctx, attr, None)
            if value is not None:
                return value
        return decorator_spec

    def run_decorated(
        self,
        func: Callable,
        manager,
        args: tuple,
        kwargs: dict,
        *,
        object_type: str | Callable,
        object_id_attr: str | Callable | None,
        skip_when: Callable | None,
        func_params: list[str],
        resolve_type: str | None = None,
        operation: str | Callable | None = None,
        subresource_type: str | Callable | None = None,
        subresource: str | Callable | None = None,
        object_version: int | str | Callable | None = None,
    ) -> Any:
        """Execute a decorated manager method with operation audit when configured."""
        bound_args = bind_args(func_params, args, kwargs)
        if skip_when is not None and invoke(skip_when, manager, bound_args):
            return func(manager, *args, **kwargs)

        if not self.should_audit_operation(resolve_related=resolve_type is not None):
            return func(manager, *args, **kwargs)

        resolved_object_type = invoke(object_type, manager, bound_args) if callable(object_type) else object_type
        resolved_object_id = resolve_resource(manager, object_id_attr, bound_args)

        self.begin_operation(
            str(resolved_object_type),
            str(resolved_object_id) if resolved_object_id else None,
        )
        if resolve_type:
            self.set_resolve(resolve_type=resolve_type)

        parent_ctx = _audit_operation_context.get()
        _audit_operation_context.set(AuditEventContext())
        try:
            result = func(manager, *args, **kwargs)
        except PermissionDenied as exc:
            body_ctx = _take_audit_context()
            if parent_ctx is not None:
                _audit_operation_context.set(parent_ctx)
            self._apply_post_fields(
                manager,
                bound_args,
                None,
                operation=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "operation", operation),
                ),
                subresource_type=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "subresource_type", subresource_type),
                ),
                subresource=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "subresource", subresource),
                ),
                object_version=self._merge_post_field_spec(body_ctx, "object_version", object_version),
            )
            event = self._finalize_operation(permission_ok=False, error=str(exc))
            self._attach_audit_event_id(exc, event)
            raise
        except Exception as exc:
            body_ctx = _take_audit_context()
            if parent_ctx is not None:
                _audit_operation_context.set(parent_ctx)
            self._apply_post_fields(
                manager,
                bound_args,
                None,
                operation=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "operation", operation),
                ),
                subresource_type=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "subresource_type", subresource_type),
                ),
                subresource=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "subresource", subresource),
                ),
                object_version=self._merge_post_field_spec(body_ctx, "object_version", object_version),
            )
            event = self._finalize_operation(permission_ok=True, error=str(exc))
            self._attach_audit_event_id(exc, event)
            raise
        else:
            body_ctx = _take_audit_context()
            if parent_ctx is not None:
                _audit_operation_context.set(parent_ctx)
            self._apply_post_fields(
                manager,
                bound_args,
                result,
                operation=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "operation", operation),
                ),
                subresource_type=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "subresource_type", subresource_type),
                ),
                subresource=cast(
                    "str | Callable | None",
                    self._merge_post_field_spec(body_ctx, "subresource", subresource),
                ),
                object_version=self._merge_post_field_spec(body_ctx, "object_version", object_version),
            )
            self._finalize_operation(permission_ok=True)
            return result

    def _apply_post_fields(
        self,
        manager,
        bound_args: dict,
        result,
        *,
        operation: str | Callable | None,
        subresource_type: str | Callable | None,
        subresource: str | Callable | None,
        object_version: int | str | Callable | None,
    ) -> None:
        if self._draft is None:
            return

        resolved_operation = self._resolve_post_value(operation, manager, bound_args, result)
        if resolved_operation is not None:
            self.set_operation(str(resolved_operation))

        resolved_version = self._resolve_post_value(object_version, manager, bound_args, result)
        if resolved_version is not None and resolved_version != "":
            try:
                self._draft.object_version = int(resolved_version)
            except (TypeError, ValueError):
                pass

        resolved_sr_type = self._resolve_post_value(subresource_type, manager, bound_args, result)
        resolved_sr = self._resolve_post_value(subresource, manager, bound_args, result)
        if resolved_sr_type or resolved_sr:
            self.set_subresource(
                subresource_type=str(resolved_sr_type) if resolved_sr_type else None,
                subresource=str(resolved_sr) if resolved_sr is not None else None,
            )

    def begin_resolve_request(self, config_path: str) -> AuditManager:
        return (
            self.begin(AuditEvent.EVENT_KIND_RESOLVE_REQUEST)
            .set_object("config", config_path)
            .set_resolve(resolve_type=AuditEvent.RESOLVE_TYPE_DIRECT)
            .set_operation(OP_RESOLVE)
        )

    def save(self) -> AuditEvent | None:
        if self._draft is None:
            raise RuntimeError("No audit draft to save")

        draft = self._draft
        self._draft = None

        if not self.should_persist(draft):
            return None

        if not draft.operation:
            draft.operation = infer_operation(draft)

        namespace_name = draft.namespace_name
        namespace_obj = draft.namespace
        if namespace_name is None and namespace_obj is not None:
            namespace_name = namespace_obj.name
        if namespace_obj is not None and not Namespace.objects.filter(pk=namespace_obj.pk).exists():
            namespace_obj = None

        try:
            event = AuditEvent.objects.create(
                client_ip=draft.client_ip,
                user_agent=draft.user_agent,
                auth_id=draft.auth_id,
                auth_email=draft.auth_email,
                auth_type=draft.auth_type,
                token_number=draft.token_number,
                namespace=namespace_obj,
                namespace_name=namespace_name,
                http_method=draft.http_method or "",
                api_endpoint=draft.api_endpoint or "",
                object_type=draft.object_type,
                object_id=draft.object_id,
                object_version=draft.object_version,
                operation=draft.operation,
                subresource_type=draft.subresource_type,
                subresource=draft.subresource,
                permission_ok=draft.permission_ok,
                error=draft.error,
                resolve_type=draft.resolve_type,
                from_cache=draft.from_cache,
                parent_event=draft.parent_event,
                event_kind=draft.event_kind,
            )
            self._last_saved = event
            if self._draft_stack:
                self._draft = self._draft_stack.pop()
            else:
                self._draft = None
            return event
        except Exception:
            logger.exception("Failed to persist audit event")
            raise

    def save_participants(
        self,
        participants: list[CacheParticipant],
        roots: set[str],
        *,
        parent: AuditEvent | None = None,
    ) -> list[AuditEvent]:
        parent_event = parent or self._last_saved
        saved: list[AuditEvent] = []

        for participant in participants:
            if participant.path in roots:
                continue
            try:
                tag_sr = tag_subresource_from_ref(participant.ref)
                builder = (
                    self.begin(AuditEvent.EVENT_KIND_RESOLVE_PARTICIPANT)
                    .set_object(participant.kind, participant.path, version=participant.version)
                    .set_resolve(
                        resolve_type=AuditEvent.RESOLVE_TYPE_NESTED,
                        from_cache=participant.from_cache,
                    )
                    .set_operation(OP_REFERENCED_IN_RESOLVE)
                    .set_outcome(permission_ok=None)
                )
                if parent_event is not None:
                    builder = builder.set_parent(parent_event)
                if tag_sr is not None:
                    builder.set_subresource(
                        subresource_type=tag_sr[0],
                        subresource=tag_sr[1],
                    )
                builder.save()
                if self._last_saved is not None:
                    saved.append(self._last_saved)
            except Exception:
                logger.exception("Failed to persist audit participant for %s", participant.path)

        return saved

    def _apply_filters(self, qs: QuerySet, filters: AuditListFilters) -> QuerySet:
        if filters.auth_id:
            qs = qs.filter(auth_id__icontains=filters.auth_id)
        if filters.auth_email:
            qs = qs.filter(auth_email__icontains=filters.auth_email)
        if filters.auth_type:
            qs = qs.filter(auth_type=filters.auth_type)
        if filters.object_type:
            qs = qs.filter(object_type=filters.object_type)
        if filters.object_id:
            qs = qs.filter(object_id__icontains=filters.object_id)
        if filters.http_method:
            qs = qs.filter(http_method__iexact=filters.http_method)
        if filters.api_endpoint:
            qs = qs.filter(api_endpoint__icontains=filters.api_endpoint)
        if filters.permission_ok is not None:
            qs = qs.filter(permission_ok=filters.permission_ok)
        if filters.resolve_type:
            qs = qs.filter(resolve_type=filters.resolve_type)
        if filters.from_cache is not None:
            qs = qs.filter(from_cache=filters.from_cache)
        if filters.event_kind:
            qs = qs.filter(event_kind=filters.event_kind)
        if filters.category == "resolve":
            qs = qs.filter(event_kind__in=_RESOLVE_EVENT_KINDS)
        elif filters.category in ("operation", "modifications"):
            qs = qs.filter(
                event_kind=AuditEvent.EVENT_KIND_OPERATION,
                http_method__in=MODIFICATION_HTTP_METHODS,
            )
        elif filters.category == "modifications-and-resolve":
            qs = qs.filter(
                Q(event_kind__in=_RESOLVE_EVENT_KINDS)
                | Q(
                    event_kind=AuditEvent.EVENT_KIND_OPERATION,
                    http_method__in=MODIFICATION_HTTP_METHODS,
                )
            )
        if filters.parent_event_id:
            qs = qs.filter(parent_event_id=filters.parent_event_id)
        if filters.client_ip:
            qs = qs.filter(client_ip__icontains=filters.client_ip)
        if filters.user_agent:
            qs = qs.filter(user_agent__icontains=filters.user_agent)
        if filters.token_number is not None:
            qs = qs.filter(token_number=filters.token_number)
        if filters.object_version is not None:
            qs = qs.filter(object_version=filters.object_version)
        if filters.operation:
            qs = qs.filter(operation__icontains=filters.operation)
        if filters.subresource_type:
            qs = qs.filter(subresource_type__icontains=filters.subresource_type)
        if filters.subresource:
            qs = qs.filter(subresource__icontains=filters.subresource)
        if filters.event_id:
            qs = qs.filter(pk=filters.event_id)
        if filters.error:
            qs = qs.filter(error__icontains=filters.error)
        if filters.namespace_name:
            qs = qs.filter(namespace_name__iexact=filters.namespace_name)
        if filters.occurred_from:
            qs = qs.filter(occurred_at__gte=filters.occurred_from)
        if filters.occurred_to:
            qs = qs.filter(occurred_at__lte=filters.occurred_to)
        return qs

    @staticmethod
    def _apply_timeline_search(qs: QuerySet, search: str) -> QuerySet:
        term = search.strip()
        if not term:
            return qs

        q = (
            Q(auth_id__icontains=term)
            | Q(auth_email__icontains=term)
            | Q(auth_type__icontains=term)
            | Q(namespace_name__icontains=term)
            | Q(http_method__icontains=term)
            | Q(api_endpoint__icontains=term)
            | Q(object_type__icontains=term)
            | Q(object_id__icontains=term)
            | Q(operation__icontains=term)
            | Q(subresource_type__icontains=term)
            | Q(subresource__icontains=term)
            | Q(error__icontains=term)
            | Q(resolve_type__icontains=term)
            | Q(event_kind__icontains=term)
            | Q(client_ip__icontains=term)
            | Q(user_agent__icontains=term)
        )

        if term.isdigit():
            number = int(term)
            q |= Q(object_version=number) | Q(token_number=number)

        lowered = term.lower()
        if lowered in ("true", "false"):
            flag = lowered == "true"
            q |= Q(from_cache=flag) | Q(permission_ok=flag)

        try:
            parsed = uuid.UUID(term)
        except ValueError:
            pass
        else:
            q |= Q(pk=parsed) | Q(parent_event_id=parsed)

        return qs.filter(q)

    @staticmethod
    def _folder_descendant_path_filter(folder_path: str) -> Q:
        """Match audit object_id for configs under a folder (inclusive)."""
        normalized = folder_path.strip("/")
        if not normalized:
            return Q(object_id__isnull=False) & ~Q(object_id="")
        return Q(object_id=normalized) | Q(object_id__startswith=f"{normalized}/")

    @staticmethod
    def _collect_prior_paths_from_moves(
        namespace_name: str,
        path: str,
        object_type: str,
    ) -> set[str]:
        """Return former paths for *path* by walking recorded move events."""
        normalized = path.strip("/")
        prior: set[str] = set()
        frontier = [normalized]
        while frontier:
            destination = frontier.pop()
            sources = (
                AuditEvent.objects.filter(
                    namespace_name__iexact=namespace_name,
                    event_kind=AuditEvent.EVENT_KIND_OPERATION,
                    operation=OP_MOVE_ITEM,
                    object_type=object_type,
                    subresource_type="path",
                    subresource=destination,
                )
                .exclude(object_id="")
                .values_list("object_id", flat=True)
                .distinct()
            )
            for source in sources:
                source_path = str(source).strip("/")
                if not source_path or source_path in prior:
                    continue
                prior.add(source_path)
                frontier.append(source_path)
        return prior

    @staticmethod
    def _item_timeline_object_id_filter(
        object_id: str,
        prior_paths: set[str],
    ) -> Q:
        paths = {object_id.strip("/")} | prior_paths
        if len(paths) == 1:
            return Q(object_id=next(iter(paths)))
        return Q(object_id__in=paths)

    def _validate_timeline_object(self, object_id: str, object_type: str) -> None:
        from ..tree import TreeManager

        if self.namespace is None:
            raise ValueError("item timeline requires a namespace")

        tree = TreeManager(self.namespace, object_id, auth=self.auth)
        if tree.item is None:
            raise NotFound(f"Item wasn't found by path '{object_id}'")
        if tree.item.node_type != object_type:
            raise NotFound(f"Item wasn't found by path '{object_id}'")

    @require_permissions(_item_audit_access)
    def item_timeline(
        self,
        object_id: str,
        object_type: str,
        *,
        search: str | None = None,
    ) -> QuerySet:
        """Audit events for one tree item as a user-friendly timeline."""
        self._validate_timeline_object(object_id, object_type)

        prior_paths = self._collect_prior_paths_from_moves(
            self.namespace.name,
            object_id,
            object_type,
        )
        filters = AuditListFilters(
            object_type=object_type,
            category="modifications",
        )
        qs = AuditEvent.objects.select_related("namespace", "parent_event").filter(
            namespace_name__iexact=self.namespace.name,
        )
        qs = self._apply_filters(qs, filters)
        qs = qs.filter(self._item_timeline_object_id_filter(object_id, prior_paths))
        qs = qs.filter(
            Q(error__isnull=True) | Q(error=""),
        ).exclude(permission_ok=False)
        if search:
            qs = self._apply_timeline_search(qs, search)
        return qs.order_by("-occurred_at", "-id")

    @require_permissions(_audit_list_access)
    def list(
        self,
        filters: AuditListFilters | None = None,
        *,
        search: str | None = None,
    ) -> QuerySet:
        filters = filters or AuditListFilters()

        qs = AuditEvent.objects.select_related("namespace", "parent_event").all()

        if self.namespace is not None:
            qs = qs.filter(namespace_name__iexact=self.namespace.name)
        elif filters.namespace_name:
            qs = qs.filter(namespace_name__iexact=filters.namespace_name)

        qs = self._apply_filters(qs, filters)

        if search:
            qs = qs.filter(
                Q(auth_id__icontains=search)
                | Q(auth_email__icontains=search)
                | Q(namespace_name__icontains=search)
                | Q(object_id__icontains=search)
                | Q(api_endpoint__icontains=search)
                | Q(operation__icontains=search)
                | Q(error__icontains=search)
            )

        return qs.order_by("-occurred_at", "-id")

    _MIN_EVENT_ID_PREFIX_LEN = 4

    def resolve_event_id(self, event_id_ref: str) -> UUID:
        """Resolve a full event UUID from a complete value or unique hex prefix."""
        ref = event_id_ref.strip()
        if not ref:
            raise ValueError("Audit event id must not be empty.")
        try:
            return uuid.UUID(ref)
        except ValueError:
            hex_prefix = ref.replace("-", "").lower()
            if not re.fullmatch(r"[0-9a-f]+", hex_prefix):
                raise ValueError(f"Invalid audit event id {ref!r}.") from None
            if len(hex_prefix) < self._MIN_EVENT_ID_PREFIX_LEN:
                raise ValueError(
                    f"Audit event id prefix {ref!r} is too short; "
                    f"use at least {self._MIN_EVENT_ID_PREFIX_LEN} hex characters."
                ) from None

        from django.db.models import CharField, Value
        from django.db.models.functions import Cast, Lower, Replace

        qs = AuditEvent.objects.all()
        if self.namespace is not None:
            qs = qs.filter(namespace_name__iexact=self.namespace.name)

        matches = list(
            qs.annotate(id_hex=Lower(Replace(Cast("id", CharField(max_length=36)), Value("-"), Value(""))))
            .filter(id_hex__startswith=hex_prefix)
            .order_by("id")[:2]
        )
        if not matches:
            raise NotFound(f"Audit event '{ref}' not found")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous audit event id prefix {ref!r}; use a longer prefix.")
        return matches[0].id

    @require_permissions(_audit_list_access)
    def get(self, event_id) -> AuditEvent:
        resolved_id = self.resolve_event_id(str(event_id))
        qs = AuditEvent.objects.select_related("namespace", "parent_event")
        if self.namespace is not None:
            qs = qs.filter(namespace_name__iexact=self.namespace.name)
        try:
            return qs.get(pk=resolved_id)
        except AuditEvent.DoesNotExist as exc:
            raise NotFound(f"Audit event '{event_id}' not found") from exc

    def config_resolve_stats(
        self,
        config_path: str,
        since: datetime,
        until: datetime,
    ) -> ResolveStats:
        if self.namespace is None:
            raise ValueError("config_resolve_stats requires a namespace")

        direct = AuditEvent.objects.filter(
            namespace_name=self.namespace.name,
            event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST,
            object_type="config",
            object_id=config_path,
            occurred_at__gte=since,
            occurred_at__lte=until,
        ).count()
        nested = AuditEvent.objects.filter(
            namespace_name=self.namespace.name,
            event_kind=AuditEvent.EVENT_KIND_RESOLVE_PARTICIPANT,
            resolve_type=AuditEvent.RESOLVE_TYPE_NESTED,
            object_type="config",
            object_id=config_path,
            occurred_at__gte=since,
            occurred_at__lte=until,
        ).count()
        return ResolveStats(direct=direct, nested=nested)

    def _resolve_events_for_stats(
        self,
        *,
        object_id: str,
        object_type: str | None,
        since: datetime,
        until: datetime,
    ) -> QuerySet:
        if self.namespace is None:
            raise ValueError("resolve stats require a namespace")

        base = AuditEvent.objects.filter(
            namespace_name=self.namespace.name,
            occurred_at__gte=since,
            occurred_at__lt=until,
        )

        if object_type == "resolver":
            return base.filter(
                event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST,
                auth_type=AuditEvent.AUTH_TYPE_RESOLVER,
                auth_id=object_id,
            )

        if object_type == "folder":
            path_filter = self._folder_descendant_path_filter(object_id)
            scoped = base.filter(object_type="config").filter(path_filter)
            direct_q = Q(event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST)
            nested_q = Q(
                event_kind=AuditEvent.EVENT_KIND_RESOLVE_PARTICIPANT,
                resolve_type=AuditEvent.RESOLVE_TYPE_NESTED,
            )
            return scoped.filter(direct_q | nested_q)

        base = base.filter(object_id=object_id)
        if object_type:
            base = base.filter(object_type=object_type)

        direct_q = Q(event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST)
        nested_q = Q(
            event_kind=AuditEvent.EVENT_KIND_RESOLVE_PARTICIPANT,
            resolve_type=AuditEvent.RESOLVE_TYPE_NESTED,
        )
        return base.filter(direct_q | nested_q)

    @require_permissions(_item_audit_access)
    def resolve_stats_series(
        self,
        *,
        object_id: str,
        object_type: str | None,
        since: datetime,
        until: datetime,
        bucket_seconds: int,
    ) -> builtins.list[ResolveSeriesBucket]:
        if bucket_seconds < 60:
            raise ValueError("bucket_seconds must be at least 60")

        if object_type is None:
            raise ValueError("object_type is required")

        self._validate_timeline_object(object_id, object_type)

        if since.tzinfo is None or until.tzinfo is None:
            raise ValueError("since and until must be timezone-aware")

        aligned_epoch = (int(since.timestamp()) // bucket_seconds) * bucket_seconds
        aligned_start = datetime.fromtimestamp(aligned_epoch, tz=since.tzinfo)
        span_seconds = max(bucket_seconds, int((until - aligned_start).total_seconds()))
        bucket_count = max(1, math.ceil(span_seconds / bucket_seconds))

        counts: dict[int, dict[str, int]] = {
            index: {"direct": 0, "nested": 0, "errors": 0} for index in range(bucket_count)
        }

        qs = self._resolve_events_for_stats(
            object_id=object_id,
            object_type=object_type,
            since=aligned_start,
            until=until,
        )
        for row in qs.values("occurred_at", "event_kind", "resolve_type", "error"):
            occurred_at = row["occurred_at"]
            if occurred_at.tzinfo is None:
                occurred_at = timezone.make_aware(occurred_at)
            index = int((occurred_at - aligned_start).total_seconds() // bucket_seconds)
            if index < 0 or index >= bucket_count:
                continue
            if row["event_kind"] == AuditEvent.EVENT_KIND_RESOLVE_REQUEST:
                counts[index]["direct"] += 1
                if row.get("error"):
                    counts[index]["errors"] += 1
            elif (
                row["event_kind"] == AuditEvent.EVENT_KIND_RESOLVE_PARTICIPANT
                and row["resolve_type"] == AuditEvent.RESOLVE_TYPE_NESTED
            ):
                counts[index]["nested"] += 1

        step = timedelta(seconds=bucket_seconds)
        return [
            ResolveSeriesBucket(
                start=aligned_start + step * index,
                direct=counts[index]["direct"],
                nested=counts[index]["nested"],
                errors=counts[index]["errors"],
            )
            for index in range(bucket_count)
        ]

    @staticmethod
    def get_audit_mode() -> str:
        """Return the validated audit mode from settings."""
        mode = getattr(settings, "OCMO_AUDIT_MODE", AUDIT_MODE_RESOLVE)
        if mode in VALID_AUDIT_MODES:
            return mode
        logger.warning("Invalid OCMO_AUDIT_MODE %r; falling back to %r", mode, AUDIT_MODE_RESOLVE)
        return AUDIT_MODE_RESOLVE

    def is_modification_request(self) -> bool:
        request = self.request
        if request is None:
            return False
        method = (getattr(request, "method", "") or "").upper()
        return method in MODIFICATION_HTTP_METHODS

    def should_persist(self, draft: AuditEventDraft) -> bool:
        mode = self.get_audit_mode()
        if mode == AUDIT_MODE_ALL:
            return True
        if _is_resolve_event(draft):
            return True
        if mode == AUDIT_MODE_MODIFICATIONS_AND_RESOLVE:
            return self.is_modification_request()
        return False

    def should_audit_operation(self, *, resolve_related: bool) -> bool:
        mode = self.get_audit_mode()
        if mode == AUDIT_MODE_ALL:
            return True
        if resolve_related:
            return True
        if mode == AUDIT_MODE_MODIFICATIONS_AND_RESOLVE:
            return self.is_modification_request()
        return False

    @classmethod
    def resolve_request(cls, config_path: str) -> _ResolveAuditRecorder:
        """Context manager: persist resolve_request + participants on exit."""
        return _ResolveAuditRecorder(cls.current(), config_path)


class _ResolveAuditRecorder:
    """Record one resolve request and optional participant rows when the block ends."""

    def __init__(self, audit_mgr: AuditManager | None, config_path: str) -> None:
        self._audit_mgr = audit_mgr
        self._config_path = config_path
        self.participants: list[CacheParticipant] = []
        self.error: str | None = None

    def __enter__(self) -> _ResolveAuditRecorder:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._audit_mgr is None:
            return
        error = str(exc_val) if exc_val is not None else self.error
        try:
            event = (
                self._audit_mgr.begin_resolve_request(self._config_path)
                .set_outcome(
                    permission_ok=True,
                    error=error,
                )
                .save()
            )
            if exc_val is not None:
                AuditManager._attach_audit_event_id(exc_val, event)
            if self.participants:
                self._audit_mgr.save_participants(
                    self.participants,
                    roots={self._config_path},
                )
        except Exception:
            logger.exception("Failed to record resolve audit for %s", self._config_path)
        return


def _is_resolve_event(draft: AuditEventDraft) -> bool:
    if draft.event_kind in _RESOLVE_EVENT_KINDS:
        return True
    return draft.resolve_type is not None
