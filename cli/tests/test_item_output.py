"""Tests for tree item output formatting."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ocmo_cli._item_output import (
    deleted_version_edit_error,
    emit_item_raw,
    emit_item_result,
    item_body,
    item_version_is_deleted,
    uses_item_output,
)


def _config_item(
    *,
    path: str = "app/web",
    data: str = "replicas: 3\n",
    version: int = 1,
    deleted_at: str | None = None,
    updater: str = "alice",
) -> SimpleNamespace:
    return SimpleNamespace(
        name="web",
        path=path,
        node_type="config",
        author="alice",
        description="",
        tags=SimpleNamespace(to_dict=lambda: {}),
        version_data=SimpleNamespace(
            version=version,
            tags=[],
            data=data,
            updater=updater,
            updated_at="2026-01-01T00:00:00+00:00",
            deleted_at=deleted_at,
            to_dict=lambda: {
                "version": version,
                "tags": [],
                "data": data,
                "updater": updater,
                "updated_at": "2026-01-01T00:00:00+00:00",
                "deleted_at": deleted_at,
            },
        ),
        to_dict=lambda: {
            "name": "web",
            "path": path,
            "node_type": "config",
            "author": "alice",
            "description": "",
            "tags": {},
            "version_data": {
                "version": version,
                "tags": [],
                "data": data,
                "updater": updater,
                "updated_at": "2026-01-01T00:00:00+00:00",
                "deleted_at": deleted_at,
            },
        },
    )


def test_item_version_is_deleted_for_deleted_config_version() -> None:
    item = _config_item(
        data="",
        version=2,
        deleted_at="2026-02-15T10:30:00+00:00",
        updater="bob",
    )
    assert item_version_is_deleted(item) is True
    assert deleted_version_edit_error("app/web", item) == ("Cannot edit deleted version 2 of 'app/web'.")


def test_item_version_is_deleted_false_for_active_version() -> None:
    assert item_version_is_deleted(_config_item()) is False


def test_uses_item_output_for_create_config() -> None:
    item = _config_item()
    assert uses_item_output("create_config", "create", "config", item) is True


def test_uses_item_output_for_update_config() -> None:
    item = _config_item()
    assert uses_item_output("update_config", "update", "config", item) is True


def test_uses_item_output_false_for_create_namespace() -> None:
    assert uses_item_output("create_namespace", "create", "namespace", object()) is False


def test_uses_item_output_false_for_create_lock() -> None:
    assert uses_item_output("create_lock", "create", "lock", object()) is False


def test_uses_item_output_for_get_item_config_only() -> None:
    item = _config_item()
    assert uses_item_output("get_item", "get", "item", item) is True
    folder = SimpleNamespace(node_type="folder", path="app", name="app")
    assert uses_item_output("get_item", "get", "item", folder) is False


def test_emit_item_raw_metadata_stderr_content_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_item_raw(_config_item(), no_color=True)
    captured = capsys.readouterr()
    assert "# path: app/web" in captured.err
    assert "# node_type: config" in captured.err
    assert "# version: 1" in captured.err
    assert captured.out == "replicas: 3\n"


def test_emit_item_result_json(capsys: pytest.CaptureFixture[str]) -> None:
    emit_item_result(_config_item(), "json")
    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == "app/web"
    assert payload["version_data"]["data"] == "replicas: 3\n"


def test_emit_item_raw_shows_deleted_version_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    item = _config_item(
        data="",
        version=2,
        deleted_at="2026-02-15T10:30:00+00:00",
        updater="bob",
    )
    emit_item_raw(item, no_color=True)
    captured = capsys.readouterr()
    assert "# version: 2" in captured.err
    assert "# deleted_at:" in captured.err
    assert "# deleted_by: bob" in captured.err
    assert "# updater:" not in captured.err
    assert "# updated_at:" not in captured.err


def test_item_body_resolver_uses_configuration() -> None:
    item = SimpleNamespace(
        node_type="resolver",
        configuration="hooks: {}\n",
        version_data=None,
    )
    assert item_body(item) == "hooks: {}\n"


def test_emit_item_raw_globalpermission_metadata_and_rule_body(
    capsys: pytest.CaptureFixture[str],
) -> None:
    item = SimpleNamespace(
        id="ead38b7a-515d-4bd3-afb4-99715746c858",
        position=1.0,
        created_at="2026-08-21T19:54:26.240000+00:00",
        updated_at="2026-08-21T19:54:26.343000+00:00",
        rule={
            "namespace": "dev-*",
            "id": "dev-read",
            "read": {
                "actors": [
                    {"kind": "User", "claims": {"email": "admin@example.com"}},
                ],
            },
        },
    )
    emit_item_raw(item, no_color=True, resource="globalpermission")
    captured = capsys.readouterr()
    assert "# id: ead38b7a-515d-4bd3-afb4-99715746c858" in captured.err
    assert "# position: 1.0" in captured.err
    assert "namespace: dev-*" in captured.out
    assert "email: admin@example.com" in captured.out
    assert "position:" not in captured.out
    assert "created_at:" not in captured.out
    assert "rule:" not in captured.out
