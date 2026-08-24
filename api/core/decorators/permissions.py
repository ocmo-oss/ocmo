"""@require_permissions decorator and PermCheck configuration."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..exceptions import CapabilityDenied, NotFound, PermissionDenied
from .binding import bind_args, invoke, resolve_resource

_NAMESPACE_PREFIX = "namespace"
_GLOBAL_PREFIX = "global"


@dataclass
class PermCheck:
    """One permission check: action on a resource with optional error masking."""

    action: str | Callable
    resource: str | Callable | None = None
    mask_as_not_found: bool = False
    not_found_message: str | Callable | None = None


def arg(name: str, transform: Callable | None = None) -> Callable:
    """Create a resource callable that extracts a named method argument."""

    def _extractor(instance, bound_args: dict) -> str:
        value = bound_args.get(name, "")
        return transform(value) if transform else value

    _extractor._is_arg_extractor = True  # type: ignore[attr-defined]
    return _extractor


def _coerce_check(check: PermCheck | str | Callable) -> PermCheck:
    if isinstance(check, PermCheck):
        return check
    return PermCheck(action=check)


def _apply_check(
    check: PermCheck,
    instance,
    bound_args: dict,
    auth,
    pm,
) -> None:
    try:
        resolved = invoke(check.action, instance, bound_args) if callable(check.action) else check.action
        if resolved is None:
            return

        if isinstance(resolved, list):
            pairs = resolved
        else:
            resource = resolve_resource(instance, check.resource, bound_args)
            pairs = [(resolved, resource)]

        for action, resource in pairs:
            type_, _, verb = action.partition(":")

            if type_ == _GLOBAL_PREFIX and verb == "admin":
                if not auth.is_global_admin:
                    raise PermissionDenied("Global administrator access required")

            elif type_ == _NAMESPACE_PREFIX:
                pm.require_namespace_object(resource, verb)

            else:
                request_ctx: dict[str, Any] = {"time": datetime.now(UTC)}
                pm.require_tree(action, resource, request_ctx)

    except PermissionDenied as exc:
        if check.mask_as_not_found:
            if check.not_found_message is None:
                msg = str(exc)
            elif callable(check.not_found_message):
                msg = check.not_found_message(instance)
            else:
                msg = check.not_found_message
            raise NotFound(msg) from exc
        raise


def require_permissions(
    *checks: PermCheck | str | Callable,
    auth_manager_attribute: str = "auth",
    namespace_attribute: str = "namespace",
) -> Callable:
    """Decorator for manager public methods."""

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
            auth = getattr(self, auth_manager_attribute, None)

            if auth is None:
                return func(self, *args, **kwargs)

            bound_args = bind_args(func_params, args, kwargs)
            namespace = getattr(self, namespace_attribute, None)
            pm = auth.permissions(namespace)

            for check in checks:
                _apply_check(_coerce_check(check), self, bound_args, auth, pm)

            try:
                return func(self, *args, **kwargs)
            except CapabilityDenied as exc:
                raise PermissionDenied(str(exc)) from exc

        return wrapper

    return decorator
