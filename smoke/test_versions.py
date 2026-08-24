"""Smoke tests for GET /~versions/{path} version history endpoint."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from ocmo_smoke.bootstrap import grant_smoke_permissions
from ocmo_smoke.client import OcmoApiClient


@pytest.fixture
def versions_namespace(api_client: OcmoApiClient) -> str:
    ns_name = f"smoke-versions-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    assert created.status_code in (200, 201), created.text
    grant_smoke_permissions(api_client, ns_name)
    yield ns_name
    api_client.delete_namespace(ns_name)


def _assert_version_list_shape(body: dict[str, Any], *, node_type: str) -> list[dict[str, Any]]:
    assert isinstance(body, dict)
    item = body.get("item")
    versions = body.get("versions")
    assert isinstance(item, dict)
    assert item.get("node_type") == node_type
    assert isinstance(versions, list)
    for row in versions:
        assert isinstance(row, dict)
        assert "version" in row
        assert "tags" in row
        assert "updater" in row
        assert "updated_at" in row
        assert "deleted_at" in row
        assert "data" not in row
    return versions


def _assert_descending_versions(versions: list[dict[str, Any]]) -> None:
    nums = [int(v["version"]) for v in versions]
    assert nums == sorted(nums, reverse=True)


@pytest.mark.smoke
def test_config_version_history(
    api_client: OcmoApiClient, versions_namespace: str
) -> None:
    path = "proj/my-config"
    assert api_client.create_config(
        versions_namespace, path, b"foo: 1\n"
    ).status_code in (200, 201)
    assert api_client.update_config(
        versions_namespace, path, b"foo: 2\n"
    ).status_code == 200
    assert api_client.update_config(
        versions_namespace, path, b"foo: 3\n"
    ).status_code == 200

    resp = api_client.list_versions(versions_namespace, path)
    assert resp.status_code == 200, resp.text
    body = resp.body
    assert isinstance(body, dict)
    versions = _assert_version_list_shape(body, node_type="config")
    assert len(versions) == 3
    _assert_descending_versions(versions)
    assert versions[0]["version"] == 3
    assert "latest" in versions[0]["tags"]


@pytest.mark.smoke
def test_template_version_history(
    api_client: OcmoApiClient, versions_namespace: str
) -> None:
    path = "tpl/app.j2"
    assert api_client.create_template(
        versions_namespace, path, b"{{ x }}\n"
    ).status_code in (200, 201)
    assert api_client.update_template(
        versions_namespace, path, b"{{ y }}\n"
    ).status_code == 200
    assert api_client.update_template(
        versions_namespace, path, b"{{ z }}\n"
    ).status_code == 200

    resp = api_client.list_versions(versions_namespace, path)
    assert resp.status_code == 200, resp.text
    body = resp.body
    assert isinstance(body, dict)
    versions = _assert_version_list_shape(body, node_type="template")
    assert len(versions) == 3
    _assert_descending_versions(versions)
    assert versions[0]["version"] == 3
    assert "latest" in versions[0]["tags"]


@pytest.mark.smoke
def test_secret_version_history_metadata_only(
    api_client: OcmoApiClient, versions_namespace: str
) -> None:
    path = "creds/db"
    assert api_client.create_secret(
        versions_namespace, path, b"password: one\n"
    ).status_code in (200, 201)
    assert api_client.update_secret(
        versions_namespace, path, b"password: two\n"
    ).status_code == 200

    resp = api_client.list_versions(versions_namespace, path)
    assert resp.status_code == 200, resp.text
    body = resp.body
    assert isinstance(body, dict)
    versions = _assert_version_list_shape(body, node_type="secret")
    assert len(versions) == 2
    _assert_descending_versions(versions)


@pytest.mark.smoke
def test_config_soft_deleted_version_still_listed(
    api_client: OcmoApiClient, versions_namespace: str
) -> None:
    path = "proj/to-prune"
    assert api_client.create_config(
        versions_namespace, path, b"v: 1\n"
    ).status_code in (200, 201)
    assert api_client.update_config(
        versions_namespace, path, b"v: 2\n"
    ).status_code == 200

    deleted = api_client.delete_item(
        versions_namespace, path, preview=False, version=1
    )
    assert deleted.status_code == 200, deleted.text

    resp = api_client.list_versions(versions_namespace, path)
    assert resp.status_code == 200, resp.text
    body = resp.body
    assert isinstance(body, dict)
    versions = _assert_version_list_shape(body, node_type="config")
    assert len(versions) == 2
    v1 = next(v for v in versions if v["version"] == 1)
    assert v1["deleted_at"] is not None


@pytest.mark.smoke
def test_versions_rejects_folder(
    api_client: OcmoApiClient, versions_namespace: str
) -> None:
    path = "only-folder/child"
    assert api_client.create_config(
        versions_namespace, path, b"x: 1\n"
    ).status_code in (200, 201)

    resp = api_client.list_versions(versions_namespace, "only-folder")
    assert resp.status_code == 422, resp.text


@pytest.mark.smoke
def test_versions_unknown_path_404(
    api_client: OcmoApiClient, versions_namespace: str
) -> None:
    resp = api_client.list_versions(versions_namespace, "no/such/item")
    assert resp.status_code == 404, resp.text
