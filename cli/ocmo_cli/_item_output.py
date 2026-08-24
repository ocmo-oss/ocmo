"""Tree item output formatting (config, template, secret, resolver)."""

from __future__ import annotations

import json
from typing import Any

from ._output import (
    _parse_path,
    _print_jsonpath_value,
    _resolve_path,
    as_dict,
    format_datetime,
    sanitize_for_output,
    yaml_dumps,
)
from ._resolve_output import _err_meta, resolve_output_format

DOCUMENT_NODE_TYPES = frozenset({"config", "template", "secret", "resolver"})

DOCUMENT_OUTPUT_RESOURCES = frozenset(
    {
        "config",
        "template",
        "secret",
        "resolver",
        "globalpermission",
    }
)

_METADATA_KEYS = ("path", "name", "node_type", "author")
_VERSION_METADATA_KEYS = ("version", "updater", "updated_at")


def uses_item_output(op_id: str, action: str, resource: str, result: Any | None) -> bool:
    """True when API result should use resolve-style raw/json/yaml output."""
    if action in ("create", "update") and resource in DOCUMENT_OUTPUT_RESOURCES:
        return True
    if op_id == "get_item" and result is not None:
        return node_type_of(result) in DOCUMENT_NODE_TYPES
    return False


def node_type_of(result: Any) -> str | None:
    if hasattr(result, "node_type"):
        value = result.node_type
        return str(value) if value else None
    if isinstance(result, dict):
        value = result.get("node_type")
        return str(value) if value else None
    return None


def _get_field(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _version_data(obj: Any) -> Any | None:
    return _get_field(obj, "version_data")


def item_version_is_deleted(result: Any) -> bool:
    """True when the fetched item points at a soft-deleted version."""
    version_data = _version_data(result)
    if version_data is None:
        return False
    return bool(_get_field(version_data, "deleted_at"))


def deleted_version_edit_error(path: str, item: Any) -> str:
    """Human-readable error for attempting to edit a deleted version."""
    version_data = _version_data(item)
    version = _get_field(version_data, "version") if version_data else None
    if version is not None:
        return f"Cannot edit deleted version {version} of {path!r}."
    return f"Cannot edit deleted version of {path!r}."


def item_metadata_rows(result: Any, *, resource: str | None = None) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []

    if resource == "namespace":
        for key in ("name", "description", "permissions_tag", "webhooks_tag", "git_sync_tag"):
            value = _get_field(result, key)
            if value is not None and value != "":
                rows.append((key, value))
        return rows

    if resource == "lock":
        for key in ("path", "reason", "locked_by"):
            value = _get_field(result, key)
            if value is not None and value != "":
                rows.append((key, value))
        expires_at = _get_field(result, "expires_at")
        if expires_at:
            rows.append(("expires_at", format_datetime(expires_at)))
        return rows

    if resource == "globalpermission":
        for key in ("id", "position", "created_at", "updated_at"):
            value = _get_field(result, key)
            if value is not None and value != "":
                if key in ("created_at", "updated_at"):
                    value = format_datetime(value) or value
                rows.append((key, value))
        return rows

    for key in _METADATA_KEYS:
        value = _get_field(result, key)
        if value is not None and value != "":
            rows.append((key, value))

    version_data = _version_data(result)
    if version_data is not None:
        deleted_at = _get_field(version_data, "deleted_at")
        version = _get_field(version_data, "version")
        if version is not None and version != "":
            rows.append(("version", version))

        if deleted_at:
            formatted_deleted_at = format_datetime(deleted_at)
            if formatted_deleted_at:
                rows.append(("deleted_at", formatted_deleted_at))
            deleted_by = _get_field(version_data, "updater")
            if deleted_by:
                rows.append(("deleted_by", deleted_by))
        else:
            for key in _VERSION_METADATA_KEYS[1:]:
                value = _get_field(version_data, key)
                if value is not None and value != "":
                    if key == "updated_at":
                        value = format_datetime(value) or value
                    rows.append((key, value))

    description = _get_field(result, "description")
    if description:
        rows.append(("description", description))

    return rows


def item_body(result: Any, *, resource: str | None = None) -> str:
    """Return the document body for stdout in raw mode."""
    if resource == "globalpermission":
        rule = _get_field(result, "rule")
        if rule is None:
            return ""
        payload = sanitize_for_output(as_dict(rule, fallback_vars=False) or rule)
        return yaml_dumps(payload)

    if resource in ("namespace", "lock"):
        payload = sanitize_for_output(as_dict(result, fallback_vars=False) or result)
        return yaml_dumps(payload)

    node_type = node_type_of(result)
    if node_type == "resolver":
        body = _get_field(result, "configuration")
        return body if isinstance(body, str) else ""
    version_data = _version_data(result)
    if version_data is not None:
        data = _get_field(version_data, "data")
        return data if isinstance(data, str) else ""
    return ""


def emit_item_metadata(result: Any, *, no_color: bool = False, resource: str | None = None) -> None:
    for key, value in item_metadata_rows(result, resource=resource):
        _err_meta(f"# {key}: {value}", no_color=no_color)


def emit_item_raw(result: Any, *, no_color: bool = False, resource: str | None = None) -> None:
    emit_item_metadata(result, no_color=no_color, resource=resource)
    text = item_body(result, resource=resource)
    print(text, end="" if text.endswith("\n") else "\n")


def emit_item_result(
    result: Any,
    fmt: str,
    *,
    no_color: bool = False,
    resource: str | None = None,
) -> None:
    """Emit one tree item in resolve-compatible output formats."""
    if fmt == "raw":
        emit_item_raw(result, no_color=no_color, resource=resource)
        return

    if fmt == "name":
        name = _get_field(result, "path") or _get_field(result, "name")
        if name:
            print(name)
        return

    payload = sanitize_for_output(as_dict(result, fallback_vars=False) or result)

    if fmt == "json":
        print(json.dumps(payload, default=str, indent=2))
    elif fmt == "yaml":
        print(yaml_dumps(payload), end="")
    elif fmt.startswith("jsonpath="):
        value = _resolve_path(payload, _parse_path(fmt[9:]))
        _print_jsonpath_value(value)
    else:
        print(payload)


def item_output_format(
    cli_fmt: str | None,
    ctx_fmt: str | None,
    *,
    command_key: str = "get item",
) -> str:
    """Effective output format for tree item commands (default: raw)."""
    return resolve_output_format(cli_fmt, ctx_fmt, command_key=command_key)


def item_output_includes_token_in_payload(fmt: str, field: str | None) -> bool:
    if field:
        return field in ("token1", "token")
    return fmt in ("yaml", "json")
