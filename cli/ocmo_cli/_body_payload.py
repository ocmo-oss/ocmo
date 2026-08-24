"""Parse and validate structured (-f) bodies for SDK BODY_PAYLOAD operations."""

from __future__ import annotations

import json
from typing import Any

__all__ = [
    "BODY_PAYLOADS",
    "format_usage_error",
    "merge_tag_address_version",
    "parse_structured_content",
    "prepare_body_payload",
    "prepare_untag_body_payload",
    "sdk_path_for_body_payload",
    "validate_create_request",
    "validate_tag_request",
]

from ._exit import USAGE_ERROR
from ._sdk_dispatch import address_keyword_for_op

try:
    from ocmo._facade_meta import BODY_PAYLOADS
except ImportError:  # pragma: no cover - CLI tests may run without SDK on path quirks
    BODY_PAYLOADS = {}


_CREATE_REQUIREMENTS: dict[str, tuple[tuple[str, ...], str]] = {
    "create_namespace": (
        ("name",),
        "create namespace requires a name (ADDRESS).",
    ),
    "create_global_permission": (
        ("namespace",),
        "create global permission requires namespace in -f " "(and optionally rule id via ADDRESS).",
    ),
    "create_lock": (
        ("reason",),
        "create lock requires --reason with a lock rationale.",
    ),
    "replace_lock": (
        ("reason",),
        "update lock requires --reason with a lock rationale.",
    ),
}

_ADDRESS_REQUIRED_OPS = frozenset({"create_lock"})

# BODY_PAYLOAD ops where ADDRESS is a positional tree path, not a body field.
_BODY_PAYLOAD_PATH_ARG_OPS = frozenset(
    {
        "create_lock",
        "replace_lock",
        "rotate_resolver_token",
        "set_tag",
    }
)

# Extra CLI kwargs that must not be merged into the rule/document body.
_BODY_PAYLOAD_EXCLUDED_EXTRA: dict[str, frozenset[str]] = {
    "create_global_permission": frozenset({"position"}),
}


def parse_structured_content(content: str) -> dict[str, Any]:
    """Parse YAML or JSON file/stdin content into an object dict."""
    import yaml  # deferred

    text = content.strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Body must be a YAML/JSON object (mapping), not a scalar or list.")
    return data


def prepare_body_payload(
    op_id: str,
    *,
    address: str | None,
    content: str | None,
    extra: dict[str, Any] | None = None,
    address_version: str | None = None,
) -> dict[str, Any]:
    """Build a dict suitable for SDK ``body=`` on BODY_PAYLOAD create/update ops."""
    if op_id not in BODY_PAYLOADS:
        return {}

    payload: dict[str, Any] = {}
    if content:
        payload = parse_structured_content(content)

    if address is not None and op_id not in _BODY_PAYLOAD_PATH_ARG_OPS:
        address_key = address_keyword_for_op(op_id)
        payload.setdefault(address_key, address)

    if extra:
        excluded = _BODY_PAYLOAD_EXCLUDED_EXTRA.get(op_id, frozenset())
        for key, value in extra.items():
            if key in excluded:
                continue
            if value is not None and value is not False:
                payload.setdefault(key, value)

    if op_id == "set_tag":
        payload = merge_tag_address_version(payload, address_version)

    return payload


def prepare_untag_body_payload(tag: str) -> dict[str, Any]:
    """POST body to remove a tag (``set_tag`` with ``version: null``)."""
    return {"tag": tag, "version": None}


def validate_tag_request(
    op_id: str,
    *,
    action: str | None = None,
    payload: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Fail fast when tag/untag commands omit required --tag."""
    import sys

    if action == "untag":
        tag = (extra or {}).get("tag")
        message = "untag item requires --tag with the version tag name to remove."
    elif op_id == "set_tag":
        tag = (payload or {}).get("tag")
        message = "tag item requires --tag with a version tag name."
    else:
        return

    if tag not in (None, ""):
        return

    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(USAGE_ERROR)


def merge_tag_address_version(
    payload: dict[str, Any],
    version: str | None,
) -> dict[str, Any]:
    """Fold ADDRESS@version into TagPayload when not already set in the body."""
    if not version or payload.get("version") not in (None, ""):
        return payload
    merged = dict(payload)
    merged["version"] = int(version) if version.isdigit() else version
    return merged


def validate_create_request(
    op_id: str,
    *,
    address: str | None,
    payload: dict[str, Any],
) -> None:
    """Fail fast with actionable CLI messages before calling the API."""
    import sys

    if op_id in _ADDRESS_REQUIRED_OPS and not address:
        print(
            "Error: create lock requires ADDRESS (tree path to lock).",
            file=sys.stderr,
        )
        raise SystemExit(USAGE_ERROR)

    spec = _CREATE_REQUIREMENTS.get(op_id)
    if spec is None:
        return

    required_fields, message = spec
    if all(payload.get(field) not in (None, "") for field in required_fields):
        return

    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(USAGE_ERROR)


def format_usage_error(exc: ValueError) -> str:
    return f"Invalid -f body: {exc}"


def sdk_path_for_body_payload(
    op_id: str,
    path: str | None,
    body_payload: dict[str, Any] | None,
) -> str | None:
    """Return the path argument for ``build_sdk_call`` (omit when merged into body)."""
    if body_payload is None:
        return path
    if op_id in _BODY_PAYLOAD_PATH_ARG_OPS:
        return path
    return None
