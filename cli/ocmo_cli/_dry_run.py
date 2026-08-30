"""User-facing dry-run plan messages for CLI commands."""

from __future__ import annotations

from typing import Any


def quote(value: str) -> str:
    return f"'{value}'"


def namespace_clause(namespace: str | None, *, client_scope: bool) -> str:
    if client_scope or not namespace:
        return ""
    return f" in namespace {quote(namespace)}"


def versioned_path(path: str | None, version: str | None) -> str:
    if not path:
        return "?"
    if version:
        return f"{quote(path)}@{version}"
    return quote(path)


def file_clause(file_path: str | None) -> str:
    if not file_path:
        return ""
    label = "<stdin>" if file_path == "-" else file_path
    return f" from {quote(label)}"


def body_dict(kwargs: dict[str, Any]) -> dict[str, Any]:
    body = kwargs.get("body")
    return body if isinstance(body, dict) else {}


def _tag_target_version_text(body: dict[str, Any], version_ref: str | None) -> str:
    """Describe the concrete version a tag dry-run would point at."""
    version_number = body.get("version")
    if version_number in (None, ""):
        return ""

    text = f" at version {version_number}"
    if not version_ref or version_ref == "latest":
        return f"{text} (latest)"
    if version_ref.isdigit() and int(version_ref) == int(version_number):
        return text
    return f"{text} ({version_ref})"


def primary_target(
    op_id: str,
    *,
    path: str | None,
    args: list[Any],
    kwargs: dict[str, Any],
) -> str | None:
    if path:
        return path
    if args:
        return str(args[0])
    for key in ("path", "name", "id", "namespace"):
        value = kwargs.get(key)
        if value not in (None, ""):
            return str(value)
    payload = body_dict(kwargs)
    for key in ("name", "id", "path"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def format_generated_dry_run(
    *,
    op_id: str,
    action: str,
    resource: str,
    path: str | None,
    version: str | None,
    namespace: str | None,
    args: list[Any],
    kwargs: dict[str, Any],
    client_scope: bool,
    file_path: str | None = None,
    gp_create_position: float | None = None,
    cast_format: str | None = None,
) -> list[str]:
    """Return human-readable dry-run plan lines (without the ``[dry-run]`` prefix)."""
    ns = namespace_clause(namespace, client_scope=client_scope)
    target = primary_target(op_id, path=path, args=args, kwargs=kwargs)
    payload = body_dict(kwargs)
    lines: list[str] = []

    if op_id == "create_namespace":
        name = target or "?"
        line = f"Would create namespace {quote(name)}."
        description = payload.get("description")
        if description:
            line += f" Description: {description!r}."
        lines.append(line)
        return lines

    if op_id == "update_namespace":
        lines.append(f"Would update namespace {quote(target or '?')}.")
        return lines

    if op_id == "delete_namespace":
        lines.append(f"Would delete namespace {quote(target or '?')}.")
        return lines

    if op_id == "create_global_permission":
        rule_id = target or payload.get("id") or "?"
        lines.append(f"Would create global permission rule {quote(str(rule_id))}{file_clause(file_path)}.")
        if gp_create_position is not None:
            lines.append(f"Would set rule position to {gp_create_position}.")
        return lines

    if op_id == "update_global_permission":
        lines.append(f"Would update global permission rule {quote(target or '?')}{file_clause(file_path)}.")
        return lines

    if op_id == "delete_global_permission":
        lines.append(f"Would delete global permission rule {quote(target or '?')}.")
        return lines

    if op_id == "move_global_permission":
        position = payload.get("position", kwargs.get("position"))
        pos_text = f" to position {position}" if position is not None else ""
        lines.append(f"Would move global permission rule {quote(target or '?')}{pos_text}.")
        return lines

    if op_id == "move_item":
        destination = payload.get("target_path") or kwargs.get("target_path")
        dest = str(destination or "?")
        lines.append(f"Would move item {quote(target or '?')} to {quote(dest)}{ns}.")
        lines.append(f"After move, item will be available at {quote(dest)}.")
        return lines

    if op_id == "copy_item":
        destination = payload.get("target_path") or kwargs.get("target_path")
        dest = str(destination or "?")
        tag = kwargs.get("tag_to_copy")
        tag_text = f" (tag {quote(str(tag))})" if tag else ""
        lines.append(f"Would copy item {quote(target or '?')} to {quote(dest)}" f"{tag_text}{ns}.")
        lines.append(f"After copy, item will be available at {quote(dest)}.")
        return lines

    if op_id == "set_tag":
        if action == "untag":
            tag = kwargs.get("tag")
            body = kwargs.get("body")
            if tag is None and isinstance(body, dict):
                tag = body.get("tag")
            lines.append(f"Would remove tag {quote(str(tag or '?'))} from item {quote(target or '?')}{ns}.")
            return lines
        tag = kwargs.get("tag")
        body = kwargs.get("body")
        if tag is None and isinstance(body, dict):
            tag = body.get("tag")
        version_text = _tag_target_version_text(payload, version)
        lines.append(
            f"Would tag item {quote(target or '?')} as {quote(str(tag or '?'))}{version_text}{ns}."
        )
        return lines

    if op_id == "rotate_resolver_token":
        token_number = kwargs.get("token_number")
        token_text = f" (token #{token_number})" if token_number is not None else ""
        lines.append(f"Would rotate resolver token for {quote(target or '?')}{token_text}{ns}.")
        return lines

    if op_id == "create_lock":
        reason = payload.get("reason") or kwargs.get("reason")
        reason_text = f" (reason: {reason!r})" if reason else ""
        expires = payload.get("expires_at") or kwargs.get("expires_at")
        expires_text = f", expires {expires}" if expires else ""
        lines.append(f"Would create lock on {quote(target or '?')}{reason_text}{expires_text}{ns}.")
        return lines

    if op_id == "replace_lock":
        reason = payload.get("reason") or kwargs.get("reason")
        reason_text = f" (reason: {reason!r})" if reason else ""
        expires = payload.get("expires_at") or kwargs.get("expires_at")
        expires_text = f", expires {expires}" if expires else ""
        lines.append(f"Would update lock on {quote(target or '?')}{reason_text}{expires_text}{ns}.")
        return lines

    if op_id == "delete_lock":
        lines.append(f"Would remove lock on {quote(target or '?')}{ns}.")
        return lines

    if op_id == "search_root" and resource == "item":
        types = kwargs.get("types") or []
        limit = kwargs.get("limit")
        type_text = f" (types: {', '.join(types)})" if types else ""
        limit_text = f", limit {limit}" if limit is not None else ""
        lines.append(f"Would list items{type_text}{limit_text}{ns}.")
        return lines

    if op_id == "list_cast_formats" and resource == "cast":
        if cast_format:
            lines.append(f"Would show cast format schema for {quote(cast_format)}{ns}.")
        else:
            lines.append(f"Would list cast formats{ns}.")
        return lines

    if op_id == "propagate_config":
        lines.append(f"Would propagate config {versioned_path(target, version)} to descendants{ns}.")
        return lines

    if op_id == "delete_item":
        if version:
            lines.append(
                f"Would delete version {quote(version)} of item {quote(target or '?')}{ns} " f"(not the item itself)."
            )
        else:
            lines.append(f"Would delete item {quote(target or '?')}{ns}.")
        return lines

    resource_label = _RESOURCE_LABELS.get(resource, resource)
    if action == "create":
        lines.append(
            f"Would create {resource_label} {versioned_path(target, version)}" f"{file_clause(file_path)}{ns}."
        )
        return lines

    if action == "update":
        lines.append(
            f"Would update {resource_label} {versioned_path(target, version)}" f"{file_clause(file_path)}{ns}."
        )
        return lines

    if action == "delete":
        lines.append(f"Would delete {resource_label} {versioned_path(target, version)}{ns}.")
        return lines

    lines.append(f"Would {action} {resource_label} {versioned_path(target, version)}{ns}.")
    return lines


def format_apply_dry_run(
    *,
    kind: str,
    path: str,
    source_name: str,
    namespace: str | None,
) -> str:
    ns = namespace_clause(namespace, client_scope=False)
    return f"Would create or update {kind} {quote(path)} from {quote(source_name)}{ns}."


def format_resolve_dry_run(
    *,
    path: str,
    namespace: str,
    cast: str | None = None,
    parameters: dict[str, Any] | None = None,
    mark_stable: bool = False,
) -> list[str]:
    lines = [f"Would resolve {quote(path)} in namespace {quote(namespace)}."]
    if cast:
        lines.append(f"Cast output as {cast}.")
    if parameters:
        params = ", ".join(f"{key}={value!r}" for key, value in sorted(parameters.items()))
        lines.append(f"Parameters: {params}.")
    if mark_stable:
        lines.append("Would advance the stable tag after resolve.")
    return lines


def format_describe_dry_run(*, path: str, namespace: str | None, char_count: int) -> str:
    ns = namespace_clause(namespace, client_scope=False)
    return f"Would update description for {quote(path)}{ns} ({char_count} characters)."


def format_edit_dry_run(*, resource: str, path: str, namespace: str | None) -> str:
    ns = namespace_clause(namespace, client_scope=False)
    label = _RESOURCE_LABELS.get(resource, resource)
    return f"Would edit {label} {quote(path)} via $EDITOR{ns}."


def format_export_dry_run(*, item_path: str, dest_file: str, namespace: str) -> str:
    return f"Would export {quote(item_path)} from namespace {quote(namespace)} " f"to {quote(dest_file)}."


def format_import_dry_run_header(count: int) -> str:
    return f"Would import {count} item{'s' if count != 1 else ''}:"


_RESOURCE_LABELS: dict[str, str] = {
    "namespace": "namespace",
    "globalpermission": "global permission rule",
    "config": "config",
    "template": "template",
    "secret": "secret",
    "resolver": "resolver",
    "item": "item",
    "lock": "lock",
    "token": "resolver token",
}


def emit_dry_run_plan(lines: list[str] | str) -> None:
    """Print one or more dry-run plan lines to stderr."""
    from ._output import status  # deferred

    if isinstance(lines, str):
        lines = [lines]
    for line in lines:
        status(f"[dry-run] {line}")
