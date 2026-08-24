"""Payload builders and response normalization for document content-type smoke tests."""

from __future__ import annotations

import json
from typing import Any

import yaml

# Canonical logical documents (YAML-shaped text after JSON coercion).
CONFIG_YAML = "foo: bar\nbaz: 42\n"
CONFIG_JSON = {"foo": "bar", "baz": 42}

TEMPLATE_TEXT = "hello: {{ name }}\n"

SECRET_YAML = "user: smoke\npass: test123\n"
SECRET_JSON = {"user": "smoke", "pass": "test123"}

RESOLVER_YAML = "cast:\n  format: yaml\n"
RESOLVER_JSON = {"cast": {"format": "yaml"}}

CONFIG_UPDATE_YAML = "updated: true\ncount: 2\n"
CONFIG_UPDATE_JSON = {"updated": True, "count": 2}

TEMPLATE_UPDATE_TEXT = "goodbye: {{ name }}\n"

SECRET_UPDATE_YAML = "user: smoke-updated\npass: rotated\n"
SECRET_UPDATE_JSON = {"user": "smoke-updated", "pass": "rotated"}

RESOLVER_UPDATE_YAML = "cast:\n  format: json\n"
RESOLVER_UPDATE_JSON = {"cast": {"format": "json"}}


def media_type_slug(media_type: str) -> str:
    return media_type.replace("/", "-").replace(".", "_")


def encode_payload(media_type: str, yaml_text: str, json_obj: dict[str, Any]) -> str | bytes:
    if media_type == "application/json":
        return json.dumps(json_obj)
    if media_type == "application/octet-stream":
        return yaml_text.encode("utf-8")
    return yaml_text


CONFIG_CREATE_PAYLOADS: dict[str, str | bytes] = {
    "application/yaml": CONFIG_YAML,
    "application/json": encode_payload("application/json", CONFIG_YAML, CONFIG_JSON),
    "application/octet-stream": encode_payload(
        "application/octet-stream", CONFIG_YAML, CONFIG_JSON
    ),
}

CONFIG_UPDATE_PAYLOADS: dict[str, str | bytes] = {
    "application/yaml": CONFIG_UPDATE_YAML,
    "application/json": encode_payload(
        "application/json", CONFIG_UPDATE_YAML, CONFIG_UPDATE_JSON
    ),
    "application/octet-stream": encode_payload(
        "application/octet-stream", CONFIG_UPDATE_YAML, CONFIG_UPDATE_JSON
    ),
}

TEMPLATE_CREATE_PAYLOADS: dict[str, str | bytes] = {
    "text/plain": TEMPLATE_TEXT,
    "text/x-jinja2": TEMPLATE_TEXT,
    "application/octet-stream": TEMPLATE_TEXT.encode("utf-8"),
}

TEMPLATE_UPDATE_PAYLOADS: dict[str, str | bytes] = {
    "text/plain": TEMPLATE_UPDATE_TEXT,
    "text/x-jinja2": TEMPLATE_UPDATE_TEXT,
    "application/octet-stream": TEMPLATE_UPDATE_TEXT.encode("utf-8"),
}

SECRET_CREATE_PAYLOADS: dict[str, str | bytes] = {
    "application/yaml": SECRET_YAML,
    "application/json": encode_payload("application/json", SECRET_YAML, SECRET_JSON),
    "application/octet-stream": encode_payload(
        "application/octet-stream", SECRET_YAML, SECRET_JSON
    ),
}

SECRET_UPDATE_PAYLOADS: dict[str, str | bytes] = {
    "application/yaml": SECRET_UPDATE_YAML,
    "application/json": encode_payload(
        "application/json", SECRET_UPDATE_YAML, SECRET_UPDATE_JSON
    ),
    "application/octet-stream": encode_payload(
        "application/octet-stream", SECRET_UPDATE_YAML, SECRET_UPDATE_JSON
    ),
}

RESOLVER_CREATE_PAYLOADS: dict[str, str | bytes] = {
    "application/yaml": RESOLVER_YAML,
    "application/json": encode_payload("application/json", RESOLVER_YAML, RESOLVER_JSON),
    "application/octet-stream": encode_payload(
        "application/octet-stream", RESOLVER_YAML, RESOLVER_JSON
    ),
}

RESOLVER_UPDATE_PAYLOADS: dict[str, str | bytes] = {
    "application/yaml": RESOLVER_UPDATE_YAML,
    "application/json": encode_payload(
        "application/json", RESOLVER_UPDATE_YAML, RESOLVER_UPDATE_JSON
    ),
    "application/octet-stream": encode_payload(
        "application/octet-stream", RESOLVER_UPDATE_YAML, RESOLVER_UPDATE_JSON
    ),
}


def parse_yaml_mapping(text: str) -> Any:
    parsed = yaml.safe_load(text)
    if parsed is None:
        return None
    return parsed


def normalize_yaml_document(text: str) -> Any:
    """Semantic equality for YAML/JSON document bodies."""
    return parse_yaml_mapping(text)


def normalize_template_document(text: str) -> str:
    return text.replace("\r\n", "\n")


def extract_stored_content(body: dict[str, Any]) -> Any:
    """Normalize stored document content from a create/update/get JSON body."""
    node_type = body.get("node_type")
    if node_type == "resolver":
        raw = body.get("configuration") or ""
        return normalize_yaml_document(raw) if raw.strip() else None
    version_data = body.get("version_data")
    if not isinstance(version_data, dict):
        raise AssertionError(f"missing version_data in response: {body!r}")
    raw = version_data.get("data")
    if raw is None:
        raise AssertionError(f"missing version_data.data for {node_type!r}: {body!r}")
    if node_type in ("config", "secret"):
        return normalize_yaml_document(raw)
    if node_type == "template":
        return normalize_template_document(raw)
    raise AssertionError(f"unsupported node_type {node_type!r}")


def assert_all_equal(
    values: list[Any],
    *,
    label: str,
) -> None:
    assert values, f"{label}: no results to compare"
    first = values[0]
    for idx, value in enumerate(values[1:], start=1):
        assert value == first, (
            f"{label}: content-type results differ at index {idx}: "
            f"first={first!r} other={value!r}"
        )
