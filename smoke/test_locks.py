"""Smoke tests for tree locking (~lock/ API and write enforcement)."""

from __future__ import annotations

import uuid

import pytest

from ocmo_smoke.bootstrap import grant_smoke_permissions
from ocmo_smoke.client import OcmoApiClient


@pytest.fixture
def lock_namespace(api_client: OcmoApiClient) -> str:
    ns_name = f"smoke-lock-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    assert created.status_code in (200, 201), created.text
    grant_smoke_permissions(api_client, ns_name)
    yield ns_name
    api_client.delete_namespace(ns_name)


@pytest.mark.smoke
def test_lock_crud_happy_path(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    assert api_client.create_config(
        lock_namespace, "app/cfg", b"key: one\n"
    ).status_code in (200, 201)

    created = api_client.create_lock(lock_namespace, "app", "prod freeze")
    assert created.status_code == 201, created.text
    assert created.body["path"] == "app"

    got = api_client.get_lock(lock_namespace, "app")
    assert got.status_code == 200, got.text

    listed = api_client.list_locks(lock_namespace)
    assert listed.status_code == 200, listed.text
    assert listed.body["count"] >= 1

    replaced = api_client.replace_lock(lock_namespace, "app", "extended freeze")
    assert replaced.status_code == 200, replaced.text

    deleted = api_client.delete_lock(lock_namespace, "app")
    assert deleted.status_code == 204, deleted.text
    assert api_client.get_lock(lock_namespace, "app").status_code == 404


@pytest.mark.smoke
def test_create_lock_conflict(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    assert api_client.create_config(
        lock_namespace, "app/cfg", b"key: one\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, "app", "first").status_code == 201
    again = api_client.create_lock(lock_namespace, "app", "second")
    assert again.status_code == 409, again.text


@pytest.mark.smoke
def test_update_blocked_under_lock(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        lock_namespace, path, b"key: one\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, "app", "freeze").status_code == 201

    blocked = api_client.update_config(lock_namespace, path, b"key: two\n")
    assert blocked.status_code == 423, blocked.text


@pytest.mark.smoke
def test_update_allowed_after_unlock(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        lock_namespace, path, b"key: one\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, "app", "freeze").status_code == 201
    assert api_client.delete_lock(lock_namespace, "app").status_code == 204

    ok = api_client.update_config(lock_namespace, path, b"key: two\n")
    assert ok.status_code == 200, ok.text


@pytest.mark.smoke
def test_create_under_locked_parent_blocked(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    assert api_client.create_config(
        lock_namespace, "app/cfg", b"key: one\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, "app", "freeze").status_code == 201

    blocked = api_client.create_config(lock_namespace, "app/new", b"key: new\n")
    assert blocked.status_code == 423, blocked.text


@pytest.mark.smoke
def test_delete_blocked(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        lock_namespace, path, b"key: one\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, path, "freeze").status_code == 201

    blocked = api_client.delete_item(lock_namespace, path, preview=False)
    assert blocked.status_code == 423, blocked.text


@pytest.mark.smoke
def test_tag_blocked(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        lock_namespace, path, b"key: one\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, path, "freeze").status_code == 201

    blocked = api_client.set_tag(lock_namespace, path, "release", version=1)
    assert blocked.status_code == 423, blocked.text


@pytest.mark.smoke
def test_get_and_resolve_unaffected(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    path = "app/cfg"
    assert api_client.create_config(
        lock_namespace, path, b"key: one\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, "app", "freeze").status_code == 201

    assert api_client.get_item(lock_namespace, path).status_code == 200
    assert api_client.resolve(lock_namespace, path).status_code == 200


@pytest.mark.smoke
def test_move_blocked_when_destination_locked(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    assert api_client.create_config(
        lock_namespace, "app/cfg", b"key: one\n"
    ).status_code in (200, 201)
    assert api_client.create_config(
        lock_namespace, "other/dest", b"key: dest\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, "other", "freeze").status_code == 201

    blocked = api_client.move_item(lock_namespace, "app/cfg", "other/moved")
    assert blocked.status_code == 423, blocked.text


@pytest.mark.smoke
def test_secret_update_blocked(
    api_client: OcmoApiClient, lock_namespace: str
) -> None:
    path = "secrets/creds"
    assert api_client.create_secret(
        lock_namespace, path, b"token: secret\n"
    ).status_code in (200, 201)
    assert api_client.create_lock(lock_namespace, path, "freeze").status_code == 201

    blocked = api_client.update_secret(
        lock_namespace, path, b"token: rotated\n"
    )
    assert blocked.status_code == 423, blocked.text
