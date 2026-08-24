"""Smoke tests for resolver token visibility and rotation."""

from __future__ import annotations

import re
import uuid

import pytest

from ocmo_smoke.bootstrap import grant_smoke_permissions
from ocmo_smoke.client import OcmoApiClient

_FULL_TOKEN = re.compile(r"^ocmort-[A-Za-z0-9_-]+$")
_MASKED_TOKEN = re.compile(r"^.{9}\*\*\*\*$")
_RESOLVER_PATH = "apps/smoke-resolver"
_RESOLVER_YAML = "cast:\n  format: yaml\n"


def _assert_full_token(value: str | None) -> None:
    assert value is not None, "expected a full token value"
    assert _FULL_TOKEN.fullmatch(value), f"expected full resolver token, got {value!r}"


def _assert_masked_token(value: str | None) -> None:
    assert value is not None, "expected a masked token value"
    assert _MASKED_TOKEN.fullmatch(value), f"expected masked resolver token, got {value!r}"


@pytest.fixture
def resolver_namespace(api_client: OcmoApiClient) -> str:
    """Isolated namespace for resolver token tests."""

    ns_name = f"smoke-resolver-tokens-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    assert created.status_code in (200, 201), created.text
    grant_smoke_permissions(api_client, ns_name)
    yield ns_name
    api_client.delete_namespace(ns_name)


@pytest.mark.resolver
def test_create_returns_token1_only(
    api_client: OcmoApiClient, resolver_namespace: str
) -> None:
    resp = api_client.create_resolver(
        resolver_namespace, _RESOLVER_PATH, _RESOLVER_YAML
    )
    assert resp.status_code == 201, resp.text
    body = resp.body
    assert isinstance(body, dict)
    _assert_full_token(body.get("token1"))
    assert body.get("token2") is None


@pytest.mark.resolver
def test_get_masks_both_tokens(
    api_client: OcmoApiClient, resolver_namespace: str
) -> None:
    api_client.create_resolver(resolver_namespace, _RESOLVER_PATH, _RESOLVER_YAML)

    get_resp = api_client.get_item(resolver_namespace, _RESOLVER_PATH)
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.body
    assert isinstance(body, dict)
    _assert_masked_token(body.get("token1"))
    assert body.get("token2") is None


@pytest.mark.resolver
def test_navigate_omits_resolver_tokens(
    api_client: OcmoApiClient, resolver_namespace: str
) -> None:
    api_client.create_resolver(resolver_namespace, _RESOLVER_PATH, _RESOLVER_YAML)

    nav_resp = api_client.navigate(resolver_namespace, "apps")
    assert nav_resp.status_code == 200, nav_resp.text
    nav = nav_resp.body
    assert isinstance(nav, dict)
    resolver_child = next(
        (c for c in nav.get("children", []) if c.get("node_type") == "resolver"),
        None,
    )
    assert resolver_child is not None
    assert set(resolver_child.keys()) == {"name", "path", "node_type"}
    assert "token1" not in resolver_child
    assert "token2" not in resolver_child


@pytest.mark.resolver
def test_describe_and_update_mask_token1(
    api_client: OcmoApiClient, resolver_namespace: str
) -> None:
    api_client.create_resolver(resolver_namespace, _RESOLVER_PATH, _RESOLVER_YAML)

    describe_resp = api_client.describe_item(
        resolver_namespace, _RESOLVER_PATH, "smoke resolver"
    )
    assert describe_resp.status_code == 200, describe_resp.text
    described = describe_resp.body
    assert isinstance(described, dict)
    _assert_masked_token(described.get("token1"))

    update_resp = api_client.update_resolver(
        resolver_namespace,
        _RESOLVER_PATH,
        "cast:\n  format: json\n",
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.body
    assert isinstance(updated, dict)
    _assert_masked_token(updated.get("token1"))


@pytest.mark.resolver
def test_rotate_returns_token_and_number(
    api_client: OcmoApiClient, resolver_namespace: str
) -> None:
    api_client.create_resolver(resolver_namespace, _RESOLVER_PATH, _RESOLVER_YAML)

    rotate_resp = api_client.rotate_resolver_token(
        resolver_namespace, _RESOLVER_PATH, 2
    )
    assert rotate_resp.status_code == 200, rotate_resp.text
    rotated = rotate_resp.body
    assert isinstance(rotated, dict)
    assert rotated.get("token_number") == 2
    _assert_full_token(rotated.get("token"))

    get_resp = api_client.get_item(resolver_namespace, _RESOLVER_PATH)
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.body
    assert isinstance(body, dict)
    _assert_masked_token(body.get("token1"))
    _assert_masked_token(body.get("token2"))
    assert body.get("token2") == f"{rotated['token'][:9]}****"


@pytest.mark.resolver
def test_rotate_token1(
    api_client: OcmoApiClient, resolver_namespace: str
) -> None:
    api_client.create_resolver(resolver_namespace, _RESOLVER_PATH, _RESOLVER_YAML)

    rotate_resp = api_client.rotate_resolver_token(
        resolver_namespace, _RESOLVER_PATH, 1
    )
    assert rotate_resp.status_code == 200, rotate_resp.text
    rotated = rotate_resp.body
    assert isinstance(rotated, dict)
    assert rotated.get("token_number") == 1
    _assert_full_token(rotated.get("token"))
