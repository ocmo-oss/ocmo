"""Smoke tests for ?mark-stable=true resolve promotion."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from ocmo_smoke.bootstrap import grant_smoke_permissions
from ocmo_smoke.client import OcmoApiClient


@pytest.fixture
def mark_stable_namespace(api_client: OcmoApiClient) -> str:
    ns_name = f"smoke-mark-stable-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    assert created.status_code in (200, 201), created.text
    grant_smoke_permissions(api_client, ns_name)
    yield ns_name
    api_client.delete_namespace(ns_name)


def _config_tags(body: dict[str, Any]) -> dict[str, int]:
    tags = body.get("tags")
    if tags is None and isinstance(body.get("item"), dict):
        tags = body["item"].get("tags")
    assert isinstance(tags, dict), body
    return tags


@pytest.mark.smoke
def test_mark_stable_promotes_on_successful_resolve(
    api_client: OcmoApiClient, mark_stable_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        mark_stable_namespace, path, b"key: one\n"
    ).status_code in (200, 201)

    resp = api_client.resolve(
        mark_stable_namespace, path, {"mark-stable": "true"}
    )
    assert resp.status_code == 200, resp.text

    got = api_client.get_item(mark_stable_namespace, path)
    assert got.status_code == 200, got.text
    assert isinstance(got.body, dict)
    assert _config_tags(got.body).get("stable") == 1


@pytest.mark.smoke
def test_resolve_without_mark_stable_leaves_tag_absent(
    api_client: OcmoApiClient, mark_stable_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        mark_stable_namespace, path, b"key: one\n"
    ).status_code in (200, 201)

    resp = api_client.resolve(mark_stable_namespace, path)
    assert resp.status_code == 200, resp.text

    got = api_client.get_item(mark_stable_namespace, path)
    assert got.status_code == 200, got.text
    assert isinstance(got.body, dict)
    assert "stable" not in _config_tags(got.body)


@pytest.mark.smoke
def test_mark_stable_is_idempotent(
    api_client: OcmoApiClient, mark_stable_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        mark_stable_namespace, path, b"key: one\n"
    ).status_code in (200, 201)

    first = api_client.resolve(
        mark_stable_namespace, path, {"mark-stable": "true"}
    )
    second = api_client.resolve(
        mark_stable_namespace, path, {"mark-stable": "true"}
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    got = api_client.get_item(mark_stable_namespace, path)
    assert got.status_code == 200, got.text
    assert isinstance(got.body, dict)
    assert _config_tags(got.body).get("stable") == 1


@pytest.mark.smoke
def test_trace_only_skips_mark_stable(
    api_client: OcmoApiClient, mark_stable_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        mark_stable_namespace, path, b"key: one\n"
    ).status_code in (200, 201)

    resp = api_client.resolve(
        mark_stable_namespace,
        path,
        {"mark-stable": "true", "trace_only": "true"},
    )
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.body, dict)
    assert resp.body.get("trace_only") is True

    got = api_client.get_item(mark_stable_namespace, path)
    assert got.status_code == 200, got.text
    assert isinstance(got.body, dict)
    assert "stable" not in _config_tags(got.body)


@pytest.mark.smoke
def test_folder_mark_stable_promotes_all_configs(
    api_client: OcmoApiClient, mark_stable_namespace: str
) -> None:
    assert api_client.create_config(
        mark_stable_namespace, "app/cfg-a", b"key: a\n"
    ).status_code in (200, 201)
    assert api_client.create_config(
        mark_stable_namespace, "app/cfg-b", b"key: b\n"
    ).status_code in (200, 201)

    resp = api_client.resolve(
        mark_stable_namespace, "app", {"mark-stable": "true"}
    )
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.body, dict)
    assert resp.body.get("length") == 2

    for path in ("app/cfg-a", "app/cfg-b"):
        got = api_client.get_item(mark_stable_namespace, path)
        assert got.status_code == 200, got.text
        assert isinstance(got.body, dict)
        assert _config_tags(got.body).get("stable") == 1


@pytest.mark.smoke
def test_mark_stable_advances_after_config_update(
    api_client: OcmoApiClient, mark_stable_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        mark_stable_namespace, path, b"key: v1\n"
    ).status_code in (200, 201)

    first = api_client.resolve(
        mark_stable_namespace, path, {"mark-stable": "true"}
    )
    assert first.status_code == 200, first.text

    assert api_client.update_config(
        mark_stable_namespace, path, b"key: v2\n"
    ).status_code == 200

    second = api_client.resolve(
        mark_stable_namespace, path, {"mark-stable": "true"}
    )
    assert second.status_code == 200, second.text

    got = api_client.get_item(mark_stable_namespace, path)
    assert got.status_code == 200, got.text
    assert isinstance(got.body, dict)
    assert _config_tags(got.body).get("stable") == 2
