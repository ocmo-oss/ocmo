"""@webhook decorator for outbound event dispatch."""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any

from ..managers.webhook.main import WebhookManager
from .binding import bind_args

logger = logging.getLogger(__name__)

_UNSET = object()


def webhook(
    event,
    *,
    skip_when=None,
    path=_UNSET,
    version=None,
    tag=None,
    details=None,
    namespace_attribute: str = "namespace",
    auth_attribute: str = "auth",
):
    """Dispatch a webhook event after successful manager method execution."""

    def decorator(func: Any):
        try:
            sig = inspect.signature(func)
            func_params = [
                n for n, p in sig.parameters.items() if n != "self" and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
            ]
        except (ValueError, TypeError):
            func_params = []

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)

            bound = bind_args(func_params, args, kwargs)

            if skip_when is not None and skip_when(self, result, bound):
                return result

            event_name = event(self, result, bound) if callable(event) else event
            if not event_name:
                return result

            if path is _UNSET:
                resolved_path = getattr(self, "path", None)
            elif callable(path):
                resolved_path = path(self, result, bound)
            else:
                resolved_path = path

            resolved_version = version(self, result, bound) if callable(version) else version
            resolved_tag = tag(self, result, bound) if callable(tag) else tag
            resolved_details = details(self, result, bound) if callable(details) else details

            ns = getattr(self, namespace_attribute, None)
            auth = getattr(self, auth_attribute, None)
            if ns is None:
                return result

            try:
                mgr = WebhookManager(ns, auth=auth)
                mgr.dispatch(
                    mgr.build_event(
                        event_name,
                        path=resolved_path,
                        version=resolved_version,
                        tag=resolved_tag,
                        details=resolved_details,
                    ),
                )
            except Exception as exc:
                logger.warning("Webhook dispatch failed for %r: %s", event_name, exc)

            return result

        return wrapper

    return decorator
