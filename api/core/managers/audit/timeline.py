"""Audit operation inference and timeline note formatting."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from ...constants.audit_operations import (
    OP_COPY_ITEM,
    OP_CREATE_ITEM,
    OP_CREATE_LOCK,
    OP_CREATE_NAMESPACE,
    OP_CREATE_PERMISSION,
    OP_DELETE_ITEM,
    OP_DELETE_LOCK,
    OP_DELETE_NAMESPACE,
    OP_DELETE_PERMISSION,
    OP_DELETE_TAG,
    OP_DIFF_ITEM,
    OP_DOWNLOAD_ARTIFACT,
    OP_LIST_LOCKS,
    OP_LIST_PERMISSIONS,
    OP_LIST_VERSIONS,
    OP_MOVE_ITEM,
    OP_MOVE_PERMISSION,
    OP_NAVIGATE,
    OP_PROMOTE_STABLE_TAG,
    OP_PROPAGATE_CONFIG,
    OP_READ_LOCK,
    OP_READ_NAMESPACE,
    OP_READ_PERMISSION,
    OP_REFERENCED_IN_RESOLVE,
    OP_RESOLVE,
    OP_ROTATE_TOKEN,
    OP_SEARCH,
    OP_SET_TAG,
    OP_UPDATE_DESCRIPTION,
    OP_UPDATE_ITEM,
    OP_UPDATE_LOCK,
    OP_UPDATE_NAMESPACE,
    OP_UPDATE_PERMISSION,
)

if TYPE_CHECKING:
    from . import AuditEventDraft

_ENDPOINT_RULES: list[tuple[re.Pattern[str], dict[str, str] | str]] = [
    (re.compile(r"/~config/~create/"), OP_CREATE_ITEM),
    (re.compile(r"/~template/~create/"), OP_CREATE_ITEM),
    (re.compile(r"/~secret/~create/"), OP_CREATE_ITEM),
    (re.compile(r"/~resolver/~create/"), OP_CREATE_ITEM),
    (re.compile(r"/~config/~update/"), OP_UPDATE_ITEM),
    (re.compile(r"/~template/~update/"), OP_UPDATE_ITEM),
    (re.compile(r"/~secret/~update/"), OP_UPDATE_ITEM),
    (re.compile(r"/~resolver/~update/"), OP_UPDATE_ITEM),
    (re.compile(r"/~delete/"), OP_DELETE_ITEM),
    (re.compile(r"/~get/"), "read_typed"),
    (re.compile(r"/~diff/"), OP_DIFF_ITEM),
    (re.compile(r"/~versions/"), OP_LIST_VERSIONS),
    (re.compile(r"/~navigate/"), OP_NAVIGATE),
    (re.compile(r"/~search/"), OP_SEARCH),
    (re.compile(r"/~describe/"), OP_UPDATE_DESCRIPTION),
    (re.compile(r"/~move/"), OP_MOVE_ITEM),
    (re.compile(r"/~copy/"), OP_COPY_ITEM),
    (re.compile(r"/~propagate/"), OP_PROPAGATE_CONFIG),
    (re.compile(r"/~download/"), OP_DOWNLOAD_ARTIFACT),
    (re.compile(r"/~tag/"), {"POST": OP_SET_TAG, "PUT": OP_SET_TAG}),
    (
        re.compile(r"/~lock/"),
        {
            "GET": OP_READ_LOCK,
            "POST": OP_CREATE_LOCK,
            "PUT": OP_UPDATE_LOCK,
            "DELETE": OP_DELETE_LOCK,
        },
    ),
    (re.compile(r"/~rotate"), OP_ROTATE_TOKEN),
]


def read_operation_for_type(object_type: str | None) -> str:
    """Return a typed Read label when object_type is known."""
    if object_type in ("config", "template", "secret", "resolver", "folder"):
        return f"Read {object_type}"
    if object_type == "namespace":
        return OP_READ_NAMESPACE
    if object_type == "lock":
        return OP_READ_LOCK
    if object_type == "global_permission":
        return OP_READ_PERMISSION
    if object_type == "artifact":
        return OP_DOWNLOAD_ARTIFACT
    return "Read item"


def infer_operation(draft: AuditEventDraft) -> str:
    """Infer a user-friendly operation label from draft fields."""
    from ...models import AuditEvent

    if draft.operation:
        return draft.operation

    if draft.event_kind == AuditEvent.EVENT_KIND_RESOLVE_REQUEST:
        return OP_RESOLVE
    if draft.event_kind == AuditEvent.EVENT_KIND_RESOLVE_PARTICIPANT:
        return OP_REFERENCED_IN_RESOLVE

    endpoint = draft.api_endpoint or ""
    method = (draft.http_method or "").upper()
    object_type = draft.object_type

    if object_type == "namespace":
        if method == "GET":
            return OP_READ_NAMESPACE
        if method == "POST":
            return OP_CREATE_NAMESPACE
        if method in ("PUT", "PATCH"):
            return OP_UPDATE_NAMESPACE
        if method == "DELETE":
            return OP_DELETE_NAMESPACE

    if object_type == "global_permission":
        if method == "GET" and (draft.object_id in (None, "", "*")):
            return OP_LIST_PERMISSIONS
        if method == "GET":
            return OP_READ_PERMISSION
        if method == "POST":
            return OP_CREATE_PERMISSION
        if method in ("PUT", "PATCH"):
            return OP_UPDATE_PERMISSION
        if method == "DELETE":
            return OP_DELETE_PERMISSION

    if object_type == "lock" and method == "GET" and draft.object_id == "*":
        return OP_LIST_LOCKS

    for pattern, rule in _ENDPOINT_RULES:
        if not pattern.search(endpoint):
            continue
        if rule == "read_typed":
            return read_operation_for_type(object_type)
        if isinstance(rule, dict):
            return rule.get(method, rule.get("GET", OP_UPDATE_ITEM))
        return rule

    if object_type == "propagation":
        return OP_PROPAGATE_CONFIG
    if object_type == "artifact":
        return OP_DOWNLOAD_ARTIFACT

    if method == "GET":
        return read_operation_for_type(object_type)
    if method == "POST":
        return OP_CREATE_ITEM
    if method in ("PUT", "PATCH"):
        return OP_UPDATE_ITEM
    if method == "DELETE":
        return OP_DELETE_ITEM

    return draft.event_kind or "Unknown"


def _parse_propagation_payload(subresource: str | None) -> dict[str, Any]:
    """Parse propagation audit JSON stored in ``subresource``."""
    raw = (subresource or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {"trigger": raw}
    return data if isinstance(data, dict) else {"trigger": raw}


def _format_propagation_targets(targets: list[dict]) -> str:
    return ", ".join(
        f"`{t['path']}`@v{t['version']}" for t in targets if t.get("path") is not None and t.get("version") is not None
    )


def _parse_subresources(
    subresource_type: str | None,
    subresource: str | None,
) -> dict[str, str]:
    if not subresource:
        return {}
    types = (subresource_type or "").split(",")
    values = subresource.split(",")
    parsed: dict[str, str] = {}
    for index, value in enumerate(values):
        kind = types[index].strip() if index < len(types) else ""
        if kind:
            parsed[kind] = value
    return parsed


def _timeline_message_body(
    operation: str,
    *,
    actor: str,
    object_type: str | None,
    object_id: str | None,
    object_version: int | None,
    subresource_type: str | None,
    subresource: str | None,
) -> str:
    kind = object_type or "item"
    subresources = _parse_subresources(subresource_type, subresource)
    path = f"`{object_id}`" if object_id else kind

    if operation == OP_CREATE_ITEM:
        if object_version is not None:
            return f"{actor} created {kind} {path} (version {object_version})"
        return f"{actor} created {kind} {path}"

    if operation == OP_UPDATE_ITEM:
        if object_version is not None:
            return f"{actor} created new version of {kind} ({object_version})"
        return f"{actor} updated {kind}"

    if operation == OP_DELETE_ITEM:
        if object_version is not None:
            return f"{actor} deleted version {object_version} of {kind}"
        return f"{actor} deleted {kind} {path}"

    if operation == OP_SET_TAG:
        tag = subresources.get("tag") or subresource
        if tag and object_version is not None:
            return f"{actor} set tag `{tag}` to version {object_version}"
        if tag:
            return f"{actor} set tag `{tag}`"
        return f"{actor} set a tag on {kind}"

    if operation == OP_DELETE_TAG:
        tag = subresources.get("tag") or subresource
        if tag and object_version is not None:
            return f"{actor} removed tag `{tag}` from version {object_version}"
        if tag:
            return f"{actor} removed tag `{tag}`"
        return f"{actor} removed a tag from {kind}"

    if operation == OP_UPDATE_DESCRIPTION:
        return f"{actor} updated description of {kind}"

    if operation == OP_MOVE_ITEM:
        destination = subresources.get("path") or subresource
        if destination:
            return f"{actor} moved {kind} to `{destination}`"
        return f"{actor} moved {kind}"

    if operation == OP_COPY_ITEM:
        destination = subresources.get("path")
        tag = subresources.get("tag")
        if destination and tag:
            return f"{actor} copied {kind} to `{destination}` (tag `{tag}`)"
        if destination:
            return f"{actor} copied {kind} to `{destination}`"
        return f"{actor} copied {kind}"

    if operation == OP_PROPAGATE_CONFIG:
        data = _parse_propagation_payload(subresource)
        trigger = data.get("trigger", "")
        trigger_tag = data.get("trigger_tag", "")
        updated = data.get("targets", [])
        unchanged = data.get("unchanged", [])
        targets_str = _format_propagation_targets(updated) if updated else ""

        if trigger == "manual":
            base = f"{actor} manually propagated version {object_version}"
            if targets_str:
                return f"{base} to {targets_str}"
            if unchanged:
                paths = ", ".join(f"`{p}`" for p in unchanged)
                return f"{base}; all targets already matched ({paths})"
            return base
        if trigger == "tag" and trigger_tag:
            base = f"{actor} propagated by setting tag `{trigger_tag}` to version {object_version}"
            if targets_str:
                return f"{base}, creating {targets_str}"
            if unchanged:
                paths = ", ".join(f"`{p}`" for p in unchanged)
                return f"{base}; all targets already matched ({paths})"
            return base
        if object_version is not None:
            return f"{actor} propagated version {object_version}"
        return f"{actor} propagated {kind}"

    if operation == OP_PROMOTE_STABLE_TAG:
        tag = subresources.get("tag") or subresource or "stable"
        return f"{actor} promoted tag `{tag}` on {kind}"

    if operation == OP_ROTATE_TOKEN:
        token = subresources.get("token") or subresource
        if token:
            return f"{actor} rotated resolver token {token}"
        return f"{actor} rotated resolver token"

    if operation == OP_CREATE_LOCK:
        return f"{actor} created lock on {path}"
    if operation == OP_UPDATE_LOCK:
        return f"{actor} updated lock on {path}"
    if operation == OP_DELETE_LOCK:
        return f"{actor} deleted lock on {path}"

    if operation == OP_CREATE_NAMESPACE:
        return f"{actor} created namespace `{object_id}`"
    if operation == OP_UPDATE_NAMESPACE:
        return f"{actor} updated namespace `{object_id}`"
    if operation == OP_DELETE_NAMESPACE:
        return f"{actor} deleted namespace `{object_id}`"

    if operation == OP_CREATE_PERMISSION:
        return f"{actor} created global permission `{object_id}`"
    if operation == OP_UPDATE_PERMISSION:
        return f"{actor} updated global permission `{object_id}`"
    if operation == OP_DELETE_PERMISSION:
        return f"{actor} deleted global permission `{object_id}`"
    if operation == OP_MOVE_PERMISSION:
        return f"{actor} moved global permission `{object_id}`"

    if operation == OP_REFERENCED_IN_RESOLVE:
        return f"{actor} referenced this {kind} in a resolve"
    if operation == OP_RESOLVE:
        return f"{actor} resolved this {kind}"
    if operation.startswith("Read "):
        return f"{actor} viewed this {kind}"

    return f"{actor} {operation.lower()}"


def format_timeline_note(event) -> str:
    """Build a single user-friendly timeline sentence for an audit event."""
    operation = event.operation
    if not operation:
        from . import AuditEventDraft

        draft = AuditEventDraft(
            event_kind=event.event_kind,
            http_method=event.http_method,
            api_endpoint=event.api_endpoint,
            object_type=event.object_type,
            object_id=event.object_id,
        )
        operation = infer_operation(draft)

    actor = f"Resolver {event.auth_id}" if event.auth_type == "resolver" else f"User {event.auth_email}"
    note = _timeline_message_body(
        operation,
        actor=actor,
        object_type=event.object_type,
        object_id=event.object_id,
        object_version=event.object_version,
        subresource_type=event.subresource_type,
        subresource=event.subresource,
    )

    if event.from_cache and operation in (OP_RESOLVE, OP_REFERENCED_IN_RESOLVE):
        note += " (from cache)"

    if event.permission_ok is False:
        note += " — permission denied"
    elif event.error:
        note += f" — {event.error}"
    return note
