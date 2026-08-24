"""Smoke tests: document endpoints accept every OpenAPI content-type equivalently."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest

from ocmo_smoke.bootstrap import grant_smoke_permissions
from ocmo_smoke.client import ApiResponse, OcmoApiClient
from ocmo_smoke.content_types import (
    CONFIG_CREATE_PAYLOADS,
    CONFIG_UPDATE_PAYLOADS,
    RESOLVER_CREATE_PAYLOADS,
    RESOLVER_UPDATE_PAYLOADS,
    SECRET_CREATE_PAYLOADS,
    SECRET_UPDATE_PAYLOADS,
    TEMPLATE_CREATE_PAYLOADS,
    TEMPLATE_UPDATE_PAYLOADS,
    assert_all_equal,
    extract_stored_content,
    media_type_slug,
)

CreateFn = Callable[..., ApiResponse]
UpdateFn = Callable[..., ApiResponse]


@pytest.fixture
def content_types_namespace(api_client: OcmoApiClient) -> str:
    ns_name = f"smoke-content-types-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    assert created.status_code in (200, 201), created.text
    grant_smoke_permissions(api_client, ns_name)
    yield ns_name
    api_client.delete_namespace(ns_name)


def _stored_content(
    api_client: OcmoApiClient,
    namespace: str,
    path: str,
    node_type: str,
    response_body: dict[str, Any] | None,
) -> Any:
    if node_type == "secret":
        get_resp = api_client.get_item(namespace, path, reveal=True)
        assert get_resp.status_code == 200, get_resp.text
        body = get_resp.body
        assert isinstance(body, dict)
        return extract_stored_content(body)

    if response_body is not None:
        try:
            return extract_stored_content(response_body)
        except AssertionError:
            pass

    get_resp = api_client.get_item(namespace, path)
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.body
    assert isinstance(body, dict)
    return extract_stored_content(body)


def _assert_create_across_content_types(
    api_client: OcmoApiClient,
    namespace: str,
    *,
    label: str,
    node_type: str,
    path_prefix: str,
    payloads: dict[str, str | bytes],
    create_fn: CreateFn,
    expected_status: int = 201,
) -> None:
    stored: list[Any] = []
    for media_type, payload in payloads.items():
        path = f"{path_prefix}/create-{media_type_slug(media_type)}"
        resp = create_fn(namespace, path, payload, content_type=media_type)
        assert resp.status_code == expected_status, (
            f"{label} {media_type}: HTTP {resp.status_code}\n{resp.text}"
        )
        body = resp.body
        assert isinstance(body, dict), f"{label} {media_type}: expected JSON object body"
        stored.append(
            _stored_content(api_client, namespace, path, node_type, body)
        )
    assert_all_equal(stored, label=f"{label} create")


def _assert_update_across_content_types(
    api_client: OcmoApiClient,
    namespace: str,
    *,
    label: str,
    node_type: str,
    path_prefix: str,
    payloads: dict[str, str | bytes],
    create_fn: CreateFn,
    update_fn: UpdateFn,
    bootstrap_payload: str | bytes,
    bootstrap_content_type: str,
) -> None:
    stored: list[Any] = []
    for media_type, payload in payloads.items():
        path = f"{path_prefix}/update-{media_type_slug(media_type)}"
        created = create_fn(
            namespace,
            path,
            bootstrap_payload,
            content_type=bootstrap_content_type,
        )
        assert created.status_code == 201, (
            f"{label} bootstrap {media_type}: HTTP {created.status_code}\n{created.text}"
        )
        updated = update_fn(namespace, path, payload, content_type=media_type)
        assert updated.status_code == 200, (
            f"{label} {media_type}: HTTP {updated.status_code}\n{updated.text}"
        )
        body = updated.body
        assert isinstance(body, dict), f"{label} {media_type}: expected JSON object body"
        stored.append(
            _stored_content(api_client, namespace, path, node_type, body)
        )
    assert_all_equal(stored, label=f"{label} update")


@pytest.mark.content_types
def test_config_create_content_types(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    _assert_create_across_content_types(
        api_client,
        content_types_namespace,
        label="config",
        node_type="config",
        path_prefix="content-types/config",
        payloads=CONFIG_CREATE_PAYLOADS,
        create_fn=api_client.create_config,
    )


@pytest.mark.content_types
def test_config_update_content_types(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    _assert_update_across_content_types(
        api_client,
        content_types_namespace,
        label="config",
        node_type="config",
        path_prefix="content-types/config",
        payloads=CONFIG_UPDATE_PAYLOADS,
        create_fn=api_client.create_config,
        update_fn=api_client.update_config,
        bootstrap_payload=CONFIG_CREATE_PAYLOADS["application/yaml"],
        bootstrap_content_type="application/yaml",
    )


@pytest.mark.content_types
def test_template_create_content_types(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    _assert_create_across_content_types(
        api_client,
        content_types_namespace,
        label="template",
        node_type="template",
        path_prefix="content-types/template",
        payloads=TEMPLATE_CREATE_PAYLOADS,
        create_fn=api_client.create_template,
    )


@pytest.mark.content_types
def test_template_update_content_types(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    _assert_update_across_content_types(
        api_client,
        content_types_namespace,
        label="template",
        node_type="template",
        path_prefix="content-types/template",
        payloads=TEMPLATE_UPDATE_PAYLOADS,
        create_fn=api_client.create_template,
        update_fn=api_client.update_template,
        bootstrap_payload=TEMPLATE_CREATE_PAYLOADS["text/plain"],
        bootstrap_content_type="text/plain",
    )


@pytest.mark.content_types
def test_secret_create_content_types(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    _assert_create_across_content_types(
        api_client,
        content_types_namespace,
        label="secret",
        node_type="secret",
        path_prefix="content-types/secret",
        payloads=SECRET_CREATE_PAYLOADS,
        create_fn=api_client.create_secret,
    )


@pytest.mark.content_types
def test_secret_update_content_types(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    _assert_update_across_content_types(
        api_client,
        content_types_namespace,
        label="secret",
        node_type="secret",
        path_prefix="content-types/secret",
        payloads=SECRET_UPDATE_PAYLOADS,
        create_fn=api_client.create_secret,
        update_fn=api_client.update_secret,
        bootstrap_payload=SECRET_CREATE_PAYLOADS["application/yaml"],
        bootstrap_content_type="application/yaml",
    )


@pytest.mark.content_types
def test_resolver_create_content_types(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    _assert_create_across_content_types(
        api_client,
        content_types_namespace,
        label="resolver",
        node_type="resolver",
        path_prefix="content-types/resolver",
        payloads=RESOLVER_CREATE_PAYLOADS,
        create_fn=api_client.create_resolver,
    )


@pytest.mark.content_types
def test_resolver_update_content_types(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    _assert_update_across_content_types(
        api_client,
        content_types_namespace,
        label="resolver",
        node_type="resolver",
        path_prefix="content-types/resolver",
        payloads=RESOLVER_UPDATE_PAYLOADS,
        create_fn=api_client.create_resolver,
        update_fn=api_client.update_resolver,
        bootstrap_payload=RESOLVER_CREATE_PAYLOADS["application/yaml"],
        bootstrap_content_type="application/yaml",
    )


@pytest.mark.content_types
def test_resolver_rotate_token_json_body(
    api_client: OcmoApiClient, content_types_namespace: str
) -> None:
    """rotate-token uses a JSON Schema body (application/json only in OpenAPI)."""
    path = "content-types/resolver/rotate-target"
    created = api_client.create_resolver(
        content_types_namespace, path, RESOLVER_CREATE_PAYLOADS["application/yaml"]
    )
    assert created.status_code == 201, created.text

    rotate_resp = api_client.rotate_resolver_token(
        content_types_namespace, path, 2
    )
    assert rotate_resp.status_code == 200, rotate_resp.text
    rotated = rotate_resp.body
    assert isinstance(rotated, dict)
    assert rotated.get("token_number") == 2
    assert isinstance(rotated.get("token"), str) and rotated["token"]
