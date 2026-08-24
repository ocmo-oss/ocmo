"""Tests for ``ocmo get item`` list mode (optional ADDRESS)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._get_item_list import (
    GET_ITEM_LIST_OUTPUT_KEY,
    prepare_get_item_list_extra,
)
from ocmo_cli.commands.generated import _execute_generated
from ocmo_cli.main import cli


def test_prepare_get_item_list_extra_defaults_types() -> None:
    extra = prepare_get_item_list_extra({}, item_types=())
    assert extra["types"] == ["config", "template", "secret", "resolver"]


def test_prepare_get_item_list_extra_honors_item_types() -> None:
    extra = prepare_get_item_list_extra({"limit": 5}, item_types=("config", "secret"))
    assert extra["types"] == ["config", "secret"]
    assert extra["limit"] == 5


def test_execute_generated_get_item_list_calls_search_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_call_sdk_method(ctx, op_id, namespace, args, kwargs):
        captured["op_id"] = op_id
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            to_dict=lambda: {
                "items": [
                    {"node_type": "config", "path": "app/web", "name": "web"},
                ],
                "count": 1,
            },
        )

    monkeypatch.setattr(
        "ocmo_cli.commands.generated._call_sdk_method",
        fake_call_sdk_method,
    )

    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True

    _execute_generated(
        ctx=ctx,
        op_ids=["get_item"],
        action="get",
        resource="item",
        address=None,
        namespace="prod",
        output_fmt="table",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"limit": 10},
        item_types=("config",),
    )

    assert captured["op_id"] == "search_root"
    assert captured["kwargs"]["types"] == ["config"]
    assert captured["kwargs"]["limit"] == 10


def test_execute_generated_get_item_list_dry_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"

    _execute_generated(
        ctx=ctx,
        op_ids=["get_item"],
        action="get",
        resource="item",
        address=None,
        namespace="prod",
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"limit": 25},
        item_types=("template", "resolver"),
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Would list items (types: template, resolver), limit 25 in namespace 'prod'." in captured.err


def test_get_item_help_shows_limit_and_type() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "item", "--help"])
    assert result.exit_code == 0
    assert "--limit" in result.output
    assert "--type" in result.output
    assert "ADDRESS" in result.output


def test_get_item_list_output_key_in_manifest() -> None:
    from ocmo_cli._output_manifest import get_command_spec

    spec = get_command_spec(GET_ITEM_LIST_OUTPUT_KEY)
    assert "table" in spec.supported_formats
    assert spec.name_field == "path"
