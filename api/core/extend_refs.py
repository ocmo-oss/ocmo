"""Helpers for optional extend source references."""

from __future__ import annotations

from typing import Literal

from .exceptions import CapabilityDenied
from .managers.tree import TreeManager
from .models import TreeItem

ExtendSourceStatus = Literal["present", "missing", "invalid"]


def classify_extend_source(
    namespace,
    resolved_path: str,
    version_ref: str,
    *,
    auth=None,
) -> ExtendSourceStatus:
    """Classify whether an extend source can be resolved.

    Returns ``missing`` when the path or version/tag is absent, ``invalid`` when
    the path points at a non-config item, and ``present`` when the source exists
    and is eligible for extend. Raises :class:`CapabilityDenied` when the
    config exists but cannot be used as an extend target.
    """
    mgr = TreeManager(namespace, resolved_path, auth=auth)
    item = mgr.get_item()
    if item is None:
        return "missing"

    try:
        mgr.get_or_raise(["config"])
    except TreeItem.DoesNotExist:
        return "invalid"

    if not mgr.is_extend_target:
        raise CapabilityDenied(f"Config '{resolved_path}' cannot be used in extend")

    if not mgr.version_resolvable(version_ref):
        return "missing"

    return "present"


def extend_source_trace_key(resolved_path: str, version_ref: str) -> str:
    """Stable trace key for an extend source reference."""
    return f"{resolved_path}@{version_ref}"


def extend_source_missing_message(resolved_path: str, version: str) -> str:
    """Human-readable error when a required extend source is absent."""
    return f"Extend source config {resolved_path!r}@{version!r} not found"
