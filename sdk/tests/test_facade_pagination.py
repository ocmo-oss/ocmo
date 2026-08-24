"""Tests for implicit facade pagination and flat payload kwargs."""

import httpx

from ocmo.client import OcmoClient
from ocmo.config import OcmoConfig

_SERVER = "https://ocmo.example.com"


def _config(**kwargs) -> OcmoConfig:
    return OcmoConfig(server=_SERVER, **kwargs)


def _namespace_item(name: str, *, item_id: int) -> dict:
    return {
        "id": item_id,
        "name": name,
        "description": "",
        "permissions_tag": "main",
        "webhooks_tag": "main",
        "git_sync_tag": "main",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _config_extended(**overrides: object) -> dict:
    payload = {
        "id": 1,
        "name": "cfg",
        "path": "app/cfg",
        "node_type": "config",
        "author": "admin",
        "description": "",
        "tags": {"latest": 1, "demo": 1},
        "version_data": {
            "data": "k: v\n",
            "version": 1,
            "tags": [],
            "updater": "admin",
            "updated_at": "2026-01-01T00:00:00Z",
            "deleted_at": None,
        },
    }
    payload.update(overrides)
    return payload


def test_list_namespaces_fetches_multiple_pages(respx_mock):
    calls: list[str] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url.params.get("offset")))
        offset = int(request.url.params.get("offset", 0))
        limit = int(request.url.params.get("limit", 100))
        total = 250
        names = [f"ns-{i:03d}" for i in range(offset, min(offset + limit, total))]
        return httpx.Response(
            200,
            json={
                "count": total,
                "items": [_namespace_item(n, item_id=i) for i, n in enumerate(names)],
            },
        )

    respx_mock.get(f"{_SERVER}/api/v1/ns/").mock(side_effect=_handler)

    client = OcmoClient(config=_config())
    page = client.list_namespaces(limit=250)

    assert len(page.items) == 250
    assert page.count == 250
    assert calls == ["0", "100", "200"]
    client.close()


def test_list_namespaces_single_page_when_limit_within_page(respx_mock):
    respx_mock.get(f"{_SERVER}/api/v1/ns/").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 3,
                "items": [_namespace_item(f"ns-{i}", item_id=i) for i in range(3)],
            },
        )
    )

    client = OcmoClient(config=_config())
    page = client.list_namespaces(limit=20)

    assert len(page.items) == 3
    assert respx_mock.calls.call_count == 1
    client.close()


def test_describe_item_accepts_flat_description(respx_mock):
    respx_mock.post(f"{_SERVER}/api/v1/ns/prod/~describe/app/cfg").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1,
                "name": "cfg",
                "path": "app/cfg",
                "node_type": "config",
                "author": "admin",
                "description": "demo",
                "tags": {"latest": 1},
                "version_data": {"data": "k: v\n", "version": 1, "updater": "admin"},
            },
        )
    )

    client = OcmoClient(config=_config())
    item = client.ns("prod").describe_item("app/cfg", description="demo")

    assert item.description == "demo"
    request = respx_mock.calls.last.request
    assert request.read() == b'{"description": "demo"}'
    client.close()


def test_create_global_permission_accepts_nested_dict_read(respx_mock):
    respx_mock.post(f"{_SERVER}/api/v1/global-permissions/").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "00000000-0000-4000-8000-000000000001",
                "position": 1.0,
                "rule": {"namespace": "demo-*"},
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        )
    )

    read = {"actors": [{"kind": "User", "claims": {"email": "*"}}]}
    client = OcmoClient(config=_config())
    client.create_global_permission(namespace="demo-*", read=read)

    request = respx_mock.calls.last.request
    assert request.read() == (
        b'{"namespace": "demo-*", "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]}}'
    )
    client.close()


def test_rotate_resolver_token_accepts_int_token_number(respx_mock):
    respx_mock.post(f"{_SERVER}/api/v1/ns/prod/~resolver/~rotate-token/app/resolver").mock(
        return_value=httpx.Response(
            200,
            json={"token_number": 1, "token": "new-token"},
        )
    )

    client = OcmoClient(config=_config())
    result = client.ns("prod").rotate_resolver_token("app/resolver", token_number=1)

    assert result.token == "new-token"
    request = respx_mock.calls.last.request
    assert request.read() == b'{"token_number": 1}'
    client.close()


def test_set_tag_accepts_empty_204_body(respx_mock):
    respx_mock.post(f"{_SERVER}/api/v1/ns/prod/~tag/app/cfg").mock(return_value=httpx.Response(204))

    client = OcmoClient(config=_config())
    result = client.ns("prod").set_tag("app/cfg", tag="demo", version=1)

    assert result is not None
    assert result.details == ""
    client.close()


def test_set_tag_accepts_flat_tag(respx_mock):
    respx_mock.post(f"{_SERVER}/api/v1/ns/prod/~tag/app/cfg").mock(
        return_value=httpx.Response(200, json=_config_extended())
    )

    client = OcmoClient(config=_config())
    client.ns("prod").set_tag("app/cfg", tag="demo", version=1)

    request = respx_mock.calls.last.request
    assert request.read() == b'{"tag": "demo", "version": 1}'
    client.close()
