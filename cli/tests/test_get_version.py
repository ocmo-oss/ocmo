"""Tests for ``ocmo get version``."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._version_output import apply_version_address_query, resolve_tag_version_number
from ocmo_cli.commands.generated import _execute_generated
from ocmo_cli.main import cli


def test_apply_version_address_query_maps_numeric_suffix() -> None:
    extra: dict = {}
    apply_version_address_query(extra, "26")
    assert extra["q"] == "26"


def test_apply_version_address_query_maps_latest_to_tag_search() -> None:
    extra: dict = {}
    apply_version_address_query(extra, "latest")
    assert extra["q"] == "latest"
    assert "limit" not in extra


def test_apply_version_address_query_respects_existing_q() -> None:
    extra = {"q": "stable"}
    apply_version_address_query(extra, "26")
    assert extra["q"] == "stable"


def test_execute_generated_get_version_passes_limit_and_tagged_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_call_sdk_method(ctx, op_id, namespace, args, kwargs):
        captured["op_id"] = op_id
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            to_dict=lambda: {
                "versions": [
                    {"version": 26, "tags": ["stable"], "updated_at": "2026-05-22T19:14:13+00:00"},
                ],
                "versions_count": 1,
            },
        )

    monkeypatch.setattr(
        "ocmo_cli.commands.generated._call_sdk_method",
        fake_call_sdk_method,
    )
    monkeypatch.setattr(
        "ocmo_cli.commands.generated._load_ops_yaml",
        lambda: {"list_item_versions": {"scope": "namespace"}},
    )

    ctx = SimpleNamespace(namespace="prod", output=None, no_color=True, dry_run=False, yes=False)
    _execute_generated(
        ctx=ctx,
        op_ids=["list_item_versions"],
        action="get",
        resource="version",
        address="audit-test/new.conf@26",
        namespace="prod",
        output_fmt="table",
        dry_run=False,
        yes=False,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"limit": 5, "tagged_only": True},
    )

    assert captured["op_id"] == "list_item_versions"
    assert captured["args"] == []
    assert captured["kwargs"]["path"] == "audit-test/new.conf"
    assert captured["kwargs"]["limit"] == 5
    assert captured["kwargs"]["tagged_only"] is True
    assert captured["kwargs"]["q"] == "26"


def test_get_version_help_lists_limit_and_tagged_only() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "version", "--help"])
    assert result.exit_code == 0
    assert "--limit" in result.output
    assert "--tagged-only" in result.output
    assert "--version" in result.output


def test_resolve_tag_version_number_uses_numeric_ref_directly() -> None:
    view = MagicMock()
    assert resolve_tag_version_number(view, "app/web", "3") == 3
    view.list_item_versions.assert_not_called()


def test_resolve_tag_version_number_fetches_latest_when_ref_omitted() -> None:
    view = MagicMock()
    view.list_item_versions.return_value = SimpleNamespace(
        to_dict=lambda: {
            "versions": [{"version": 5, "tags": ["latest"], "updated_at": "2026-01-01T00:00:00Z"}],
            "versions_count": 5,
        },
    )
    assert resolve_tag_version_number(view, "app/web", None) == 5
    view.list_item_versions.assert_called_once_with(path="app/web", limit=1)


def test_resolve_tag_version_number_searches_by_tag_name() -> None:
    view = MagicMock()
    view.list_item_versions.return_value = SimpleNamespace(
        to_dict=lambda: {
            "versions": [{"version": 2, "tags": ["stable"], "updated_at": "2026-01-01T00:00:00Z"}],
            "versions_count": 1,
        },
    )
    assert resolve_tag_version_number(view, "app/web", "stable") == 2
    view.list_item_versions.assert_called_once_with(path="app/web", limit=1, q="stable")


def test_tag_item_without_version_tags_latest(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    view = MagicMock()
    view.set_tag.return_value = SimpleNamespace(to_dict=lambda: {"details": ""})

    def list_versions(**kwargs: object) -> SimpleNamespace:
        if kwargs.get("limit") == 1 and "q" not in kwargs:
            return SimpleNamespace(
                to_dict=lambda: {
                    "versions": [
                        {
                            "version": 3,
                            "tags": ["latest"],
                            "updated_at": "2026-08-09T15:06:42+00:00",
                        },
                    ],
                    "versions_count": 3,
                },
            )
        return SimpleNamespace(
            to_dict=lambda: {
                "versions": [
                    {
                        "version": 3,
                        "tags": ["test"],
                        "updated_at": "2026-08-09T15:06:42+00:00",
                    },
                ],
                "versions_count": 3,
            },
        )

    view.list_item_versions.side_effect = list_versions

    ctx = MagicMock()
    ctx.namespace = "prod"
    ctx.output = None
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    monkeypatch.setattr(
        "ocmo_cli.commands.generated._load_ops_yaml",
        lambda: {
            "set_tag": {"scope": "namespace"},
            "list_item_versions": {"scope": "namespace"},
        },
    )

    _execute_generated(
        ctx=ctx,
        op_ids=["set_tag"],
        action="tag",
        resource="item",
        address="x/confT",
        namespace="prod",
        output_fmt="table",
        dry_run=False,
        yes=False,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"tag": "test"},
    )

    view.set_tag.assert_called_once()
    set_tag_kwargs = view.set_tag.call_args.kwargs
    assert set_tag_kwargs["body"] == {"tag": "test", "version": 3}
    assert view.list_item_versions.call_count == 2


def test_tag_item_emits_version_list_like_get_version(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    view = MagicMock()
    view.set_tag.return_value = SimpleNamespace(to_dict=lambda: {"details": ""})
    view.list_item_versions.return_value = SimpleNamespace(
        to_dict=lambda: {
            "versions": [
                {
                    "version": 1,
                    "tags": ["test"],
                    "updated_at": "2026-08-09T15:06:42+00:00",
                },
            ],
            "versions_count": 1,
        },
    )

    ctx = MagicMock()
    ctx.namespace = "prod"
    ctx.output = None
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    monkeypatch.setattr(
        "ocmo_cli.commands.generated._load_ops_yaml",
        lambda: {
            "set_tag": {"scope": "namespace"},
            "list_item_versions": {"scope": "namespace"},
        },
    )

    _execute_generated(
        ctx=ctx,
        op_ids=["set_tag"],
        action="tag",
        resource="item",
        address="x/confT@1",
        namespace="prod",
        output_fmt="table",
        dry_run=False,
        yes=False,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"tag": "test"},
    )

    view.set_tag.assert_called_once()
    set_tag_kwargs = view.set_tag.call_args.kwargs
    assert set_tag_kwargs["body"] == {"tag": "test", "version": 1}
    view.list_item_versions.assert_called_once_with(path="x/confT", q="1")
    out = capsys.readouterr().out
    assert "VERSION" in out
    assert "TAGS" in out
    assert "test" in out
    assert "DETAILS" not in out


def test_untag_item_uses_set_tag_with_null_version(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    view = MagicMock()
    view.set_tag.return_value = SimpleNamespace(to_dict=lambda: {"details": ""})
    view.list_item_versions.return_value = SimpleNamespace(
        to_dict=lambda: {
            "versions": [
                {
                    "version": 2,
                    "tags": [],
                    "updated_at": "2026-08-09T15:06:42+00:00",
                },
            ],
            "versions_count": 1,
        },
    )

    ctx = MagicMock()
    ctx.namespace = "prod"
    ctx.output = None
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    monkeypatch.setattr(
        "ocmo_cli.commands.generated._load_ops_yaml",
        lambda: {
            "set_tag": {"scope": "namespace"},
            "list_item_versions": {"scope": "namespace"},
        },
    )

    _execute_generated(
        ctx=ctx,
        op_ids=["set_tag"],
        action="untag",
        resource="item",
        address="x/confT@2",
        namespace="prod",
        output_fmt="table",
        dry_run=False,
        yes=False,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"tag": "test"},
    )

    view.set_tag.assert_called_once()
    set_tag_kwargs = view.set_tag.call_args.kwargs
    assert set_tag_kwargs["body"] == {"tag": "test", "version": None}
    view.delete_tag.assert_not_called()
    view.list_item_versions.assert_called_once_with(path="x/confT", q="2")
    out = capsys.readouterr().out
    assert "VERSION" in out
    assert "TAGS" in out
