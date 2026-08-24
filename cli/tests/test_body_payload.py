"""Tests for structured create body handling."""

from __future__ import annotations

import pytest

from ocmo_cli._body_payload import (
    merge_tag_address_version,
    parse_structured_content,
    prepare_body_payload,
    prepare_untag_body_payload,
    sdk_path_for_body_payload,
    validate_create_request,
    validate_tag_request,
)
from ocmo_cli._exit import USAGE_ERROR


def test_parse_structured_content_yaml() -> None:
    assert parse_structured_content("namespace: prod\nread: {}\n") == {
        "namespace": "prod",
        "read": {},
    }


def test_prepare_body_payload_create_namespace_merges_address() -> None:
    payload = prepare_body_payload(
        "create_namespace",
        address="my-ns",
        content=None,
    )
    assert payload == {"name": "my-ns"}


def test_prepare_body_payload_create_namespace_merges_description_flag() -> None:
    payload = prepare_body_payload(
        "create_namespace",
        address="my-ns",
        content=None,
        extra={"description": "My awesome NS"},
    )
    assert payload == {"name": "my-ns", "description": "My awesome NS"}


def test_prepare_body_payload_create_global_permission_uses_id_address() -> None:
    payload = prepare_body_payload(
        "create_global_permission",
        address="rule-1",
        content="namespace: '*'\nread:\n  allow: true\n",
    )
    assert payload["id"] == "rule-1"
    assert payload["namespace"] == "*"


def test_prepare_body_payload_create_global_permission_excludes_position_flag() -> None:
    payload = prepare_body_payload(
        "create_global_permission",
        address="dev-read",
        content="namespace: 'dev/*'\nread:\n  allow: true\n",
        extra={"position": 1.5},
    )
    assert payload["id"] == "dev-read"
    assert "position" not in payload


def test_prepare_body_payload_create_lock_merges_reason_flag() -> None:
    payload = prepare_body_payload(
        "create_lock",
        address="app/web",
        content=None,
        extra={"reason": "deploy freeze"},
    )
    assert payload == {"reason": "deploy freeze"}


def test_prepare_body_payload_replace_lock_merges_reason_and_expires() -> None:
    payload = prepare_body_payload(
        "replace_lock",
        address="app/web",
        content=None,
        extra={"reason": "extended freeze", "expires_at": "2026-12-31T00:00:00Z"},
    )
    assert payload == {
        "reason": "extended freeze",
        "expires_at": "2026-12-31T00:00:00Z",
    }


def test_prepare_body_payload_set_tag_does_not_merge_path_into_body() -> None:
    payload = prepare_body_payload(
        "set_tag",
        address="x/confT",
        content=None,
        extra={"tag": "test"},
        address_version="1",
    )
    assert payload == {"tag": "test", "version": 1}
    assert "path" not in payload


def test_prepare_body_payload_rotate_resolver_token_keeps_path_out_of_body() -> None:
    payload = prepare_body_payload(
        "rotate_resolver_token",
        address="audit-test/resolver",
        content=None,
        extra={"token_number": 1},
    )
    assert payload == {"token_number": 1}
    assert "path" not in payload


def test_sdk_path_for_body_payload_rotate_resolver_token_keeps_path() -> None:
    assert (
        sdk_path_for_body_payload(
            "rotate_resolver_token",
            "audit-test/resolver",
            {"token_number": 1},
        )
        == "audit-test/resolver"
    )


def test_rotate_resolver_token_sdk_call_passes_path_and_body() -> None:
    from ocmo._facade_runtime import prepare_kwargs

    from ocmo_cli._sdk_dispatch import build_sdk_call

    body_payload = prepare_body_payload(
        "rotate_resolver_token",
        address="audit-test/resolver",
        content=None,
        extra={"token_number": 1},
    )
    args, kwargs = build_sdk_call(
        "rotate_resolver_token",
        path=sdk_path_for_body_payload(
            "rotate_resolver_token",
            "audit-test/resolver",
            body_payload,
        ),
        version=None,
        content=None,
        extra={},
    )
    if body_payload is not None:
        kwargs["body"] = body_payload
    assert args == []
    assert kwargs["path"] == "audit-test/resolver"
    prepared = prepare_kwargs("rotate_resolver_token", kwargs)
    assert prepared["path"] == "audit-test/resolver"
    assert prepared["body"].to_dict() == {"token_number": 1}


def test_merge_tag_address_version_preserves_existing_body_version() -> None:
    payload = merge_tag_address_version({"tag": "test", "version": 2}, "1")
    assert payload == {"tag": "test", "version": 2}


def test_sdk_path_for_body_payload_set_tag_keeps_path() -> None:
    assert (
        sdk_path_for_body_payload(
            "set_tag",
            "x/confT",
            {"tag": "test"},
        )
        == "x/confT"
    )


def test_set_tag_sdk_call_uses_positional_path_with_body_payload() -> None:
    from ocmo._facade_runtime import prepare_kwargs

    from ocmo_cli._sdk_dispatch import build_sdk_call

    body_payload = prepare_body_payload(
        "set_tag",
        address="x/confT",
        content=None,
        extra={"tag": "test"},
        address_version="1",
    )
    args, kwargs = build_sdk_call(
        "set_tag",
        path=sdk_path_for_body_payload("set_tag", "x/confT", body_payload),
        version="1",
        content=None,
        extra={},
    )
    if body_payload is not None:
        kwargs["body"] = body_payload
    assert args == ["x/confT"]
    prepared = prepare_kwargs("set_tag", kwargs)
    assert prepared["body"].to_dict() == {"tag": "test", "version": 1}


def test_prepare_untag_body_payload() -> None:
    assert prepare_untag_body_payload("test") == {"tag": "test", "version": None}


def test_untag_body_serializes_version_null_for_set_tag() -> None:
    from ocmo._facade_runtime import prepare_kwargs

    from ocmo_cli._sdk_dispatch import build_sdk_call

    body_payload = prepare_untag_body_payload("test")
    args, kwargs = build_sdk_call(
        "set_tag",
        path="x/confT",
        version=None,
        content=None,
        extra={},
    )
    kwargs["body"] = body_payload
    prepared = prepare_kwargs("set_tag", kwargs)
    assert args == ["x/confT"]
    assert prepared["body"].to_dict() == {"tag": "test", "version": None}


def test_validate_create_lock_requires_reason() -> None:
    with pytest.raises(SystemExit) as exc:
        validate_create_request("create_lock", address="app/web", payload={})
    assert exc.value.code == USAGE_ERROR


def test_validate_replace_lock_requires_reason() -> None:
    with pytest.raises(SystemExit) as exc:
        validate_create_request("replace_lock", address="app/web", payload={})
    assert exc.value.code == USAGE_ERROR


def test_validate_create_global_permission_requires_namespace() -> None:
    with pytest.raises(SystemExit) as exc:
        validate_create_request("create_global_permission", address="rule-1", payload={"id": "rule-1"})
    assert exc.value.code == USAGE_ERROR


def test_validate_tag_request_set_tag_requires_tag() -> None:
    with pytest.raises(SystemExit) as exc:
        validate_tag_request("set_tag", payload={"version": 2})
    assert exc.value.code == USAGE_ERROR


def test_validate_tag_request_untag_requires_tag() -> None:
    with pytest.raises(SystemExit) as exc:
        validate_tag_request("set_tag", action="untag", extra={})
    assert exc.value.code == USAGE_ERROR
