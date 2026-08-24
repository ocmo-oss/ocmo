"""Tests for SDK dispatch helpers."""

from __future__ import annotations

from ocmo_cli._sdk_dispatch import build_sdk_call, pick_op_id, unwrap_list_payload


def test_unwrap_list_payload_items() -> None:
    data = {"items": [{"name": "a"}, {"name": "b"}], "count": 2}
    assert unwrap_list_payload(data) == [{"name": "a"}, {"name": "b"}]


def test_pick_op_id_list_vs_show() -> None:
    meta = {
        "list_namespaces": {"scope": "client"},
        "show_namespace": {"scope": "client"},
    }
    assert (
        pick_op_id(
            ["list_namespaces", "show_namespace"],
            address=None,
            namespace=None,
            ops_meta=meta,
        )
        == "list_namespaces"
    )
    assert (
        pick_op_id(
            ["list_namespaces", "show_namespace"],
            address="prod",
            namespace=None,
            ops_meta=meta,
        )
        == "show_namespace"
    )


def test_build_sdk_call_create_namespace() -> None:
    args, kwargs = build_sdk_call("create_namespace", path="my-ns", version=None, content=None)
    assert args == []
    assert kwargs == {"name": "my-ns"}


def test_build_sdk_call_create_global_permission_uses_id() -> None:
    args, kwargs = build_sdk_call(
        "create_global_permission",
        path="rule-1",
        version=None,
        content=None,
    )
    assert args == []
    assert kwargs == {"id": "rule-1"}


def test_build_sdk_call_create_lock() -> None:
    args, kwargs = build_sdk_call(
        "create_lock",
        path="app/web",
        version=None,
        content=None,
        extra={"reason": "maintenance"},
    )
    assert args == ["app/web"]
    assert kwargs == {"reason": "maintenance"}


def test_build_sdk_call_show_namespace() -> None:
    args, kwargs = build_sdk_call("show_namespace", path="my-ns", version=None, content=None)
    assert args == ["my-ns"]
    assert kwargs == {}


def test_build_sdk_call_search_extra() -> None:
    args, kwargs = build_sdk_call(
        "search_root",
        path=None,
        version=None,
        content=None,
        extra={"q": "git"},
    )
    assert args == []
    assert kwargs == {"q": "git"}


def test_build_sdk_call_set_tag_untag_body_ignores_address_version() -> None:
    from ocmo_cli._body_payload import prepare_untag_body_payload

    body = prepare_untag_body_payload("test")
    args, kwargs = build_sdk_call(
        "set_tag",
        path="x/confT",
        version="2",
        content=None,
        extra={},
    )
    kwargs["body"] = body
    assert args == ["x/confT"]
    assert kwargs == {"body": {"tag": "test", "version": None}}


def test_build_sdk_call_set_tag_positional_path() -> None:
    args, kwargs = build_sdk_call(
        "set_tag",
        path="x/confT",
        version="1",
        content=None,
        extra={"tag": "test"},
    )
    assert args == ["x/confT"]
    assert kwargs == {"tag": "test"}
