"""Shared argument-binding helpers for manager method decorators."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any


def bind_args(param_names: list[str], args: tuple, kwargs: dict) -> dict[str, Any]:
    """Map positional + keyword call arguments to a name→value dict."""
    bound: dict[str, Any] = {}
    for i, name in enumerate(param_names):
        if i < len(args):
            bound[name] = args[i]
    bound.update(kwargs)
    return bound


@functools.lru_cache(maxsize=512)
def _callable_extra_params(fn: Callable) -> tuple[str, ...]:
    """Return declared parameter names beyond 'self' (cached per callable)."""
    try:
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        return tuple(p.name for p in params[1:] if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD))
    except (ValueError, TypeError):
        return ()


def invoke(fn: Callable, instance, bound_args: dict[str, Any]):
    """Call fn(instance) or fn(instance, **matching_bound_args) from its signature."""
    extra = _callable_extra_params(fn)
    if not extra:
        return fn(instance)
    kwargs = {name: bound_args[name] for name in extra if name in bound_args}
    return fn(instance, **kwargs)


def resolve_resource(instance, resource, bound_args: dict[str, Any]) -> str:
    """Resolve a resource specification to a string."""
    if resource is None:
        return getattr(instance, "path", "")
    if callable(resource):
        if getattr(resource, "_is_arg_extractor", False):
            return resource(instance, bound_args)
        return invoke(resource, instance, bound_args)
    return getattr(instance, resource, "")
