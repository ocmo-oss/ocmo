"""@audit decorator for append-only operation logging."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(slots=True)
class AuditEventContext:
    """Public post-call fields a method may supply to the active audit event."""

    operation: str | None = None
    object_version: int | None = None
    subresource_type: str | None = None
    subresource: str | None = None


_audit_operation_context: ContextVar[AuditEventContext | None] = ContextVar(
    "audit_operation_context",
    default=None,
)


def enrich_audit(**kwargs) -> None:
    """Set post-call audit fields from inside a decorated method body.

    Safe to call when no audit is active (no-op).
    Body values take precedence over decorator defaults.
    """
    ctx = _audit_operation_context.get()
    if ctx is None:
        return
    for key, value in kwargs.items():
        if value is not None and hasattr(ctx, key):
            setattr(ctx, key, value)


def _take_audit_context() -> AuditEventContext | None:
    """Consume and clear the ContextVar; called by run_decorated after func()."""
    ctx = _audit_operation_context.get()
    _audit_operation_context.set(None)
    return ctx


def audit(
    object_type: str | Callable,
    *,
    object_id_attr: str | Callable | None = None,
    namespace_attribute: str = "namespace",
    resolve_type: str | None = None,
    operation: str | Callable | None = None,
    subresource_type: str | Callable | None = None,
    subresource: str | Callable | None = None,
    object_version: int | str | Callable | None = None,
    skip_when: Callable | None = None,
    skip_when_no_auth: bool = True,
    auth_manager_attribute: str = "auth",
) -> Callable:
    """Decorator for manager public methods — logs outcome after execution."""

    def decorator(func: Callable) -> Callable:
        try:
            sig = inspect.signature(func)
            func_params = [
                name
                for name, p in sig.parameters.items()
                if name != "self" and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
            ]
        except (ValueError, TypeError):
            func_params = []

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            from ..managers.audit import AuditManager

            audit_mgr = AuditManager.for_decorated_call(
                self,
                auth_manager_attribute=auth_manager_attribute,
                skip_when_no_auth=skip_when_no_auth,
            )
            if audit_mgr is None:
                return func(self, *args, **kwargs)
            return audit_mgr.run_decorated(
                func,
                self,
                args,
                kwargs,
                object_type=object_type,
                object_id_attr=object_id_attr,
                skip_when=skip_when,
                func_params=func_params,
                resolve_type=resolve_type,
                operation=operation,
                subresource_type=subresource_type,
                subresource=subresource,
                object_version=object_version,
            )

        return wrapper

    return decorator
