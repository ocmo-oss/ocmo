"""Tests for hand-written ``ocmo timeline audit``."""

from __future__ import annotations

from unittest.mock import MagicMock

from click.testing import CliRunner

from ocmo_cli._output import format_datetime
from ocmo_cli.commands.timeline import (
    _entry_message,
    _fetch_timeline_entries,
    timeline_audit_cmd,
)
from ocmo_cli.main import cli


def test_timeline_audit_help_lists_search_and_limit() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["timeline", "audit", "--help"])
    assert result.exit_code == 0, result.output
    assert "--search" in result.output
    assert "--limit" in result.output
    assert "--object-id" not in result.output
    assert "--object-type" not in result.output
    assert "--output" not in result.output


def test_timeline_audit_rejects_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-n", "prod", "-o", "json", "timeline", "audit", "app/web"])
    assert result.exit_code != 0
    assert "does not support -o/--output" in result.output


def test_entry_message_uses_api_note() -> None:
    entry = {
        "occurred_at": "2026-08-09T15:06:42+00:00",
        "message": "User alice@example.com set tag `stable` to version 2",
    }
    occurred_at, message = _entry_message(entry)
    assert occurred_at == format_datetime(entry["occurred_at"])
    assert message == "User alice@example.com set tag `stable` to version 2"


def test_fetch_timeline_entries_respects_limit() -> None:
    items = [MagicMock() for _ in range(5)]
    page = MagicMock(items=items, count=5)
    view = MagicMock()
    view.namespace_audit_timeline.return_value = page

    entries = _fetch_timeline_entries(
        view,
        path="app/web",
        node_type="config",
        search=None,
        limit=3,
    )

    assert len(entries) == 3
    view.namespace_audit_timeline.assert_called_once_with(
        object_id="app/web",
        object_type="config",
        search=None,
        limit=3,
        offset=0,
    )


def test_fetch_timeline_entries_paginates() -> None:
    first = MagicMock(items=[MagicMock()], count=2)
    second = MagicMock(items=[MagicMock()], count=2)
    view = MagicMock()
    view.namespace_audit_timeline.side_effect = [first, second]

    entries = _fetch_timeline_entries(
        view,
        path="app/web",
        node_type="config",
        search="stable",
    )

    assert len(entries) == 2
    calls = view.namespace_audit_timeline.call_args_list
    assert len(calls) == 2
    assert calls[0].kwargs == {
        "object_id": "app/web",
        "object_type": "config",
        "search": "stable",
        "limit": 100,
        "offset": 0,
    }
    assert calls[1].kwargs["offset"] == 1


def test_timeline_audit_prints_message_notes() -> None:
    entry = MagicMock()
    entry.to_dict.return_value = {
        "occurred_at": "2026-08-09T15:06:42+00:00",
        "message": "User alice@example.com set tag `stable` to version 2",
    }
    page = MagicMock()
    page.items = [entry]
    page.count = 1

    view = MagicMock()
    view.get_item.return_value = MagicMock(node_type="config")
    view.namespace_audit_timeline.return_value = page

    ctx = MagicMock()
    ctx.output = None
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    runner = CliRunner()
    result = runner.invoke(timeline_audit_cmd, ["app/web"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "User alice@example.com set tag `stable` to version 2" in result.output
    view.namespace_audit_timeline.assert_called_once_with(
        object_id="app/web",
        object_type="config",
        search=None,
        limit=100,
        offset=0,
    )


def test_timeline_audit_passes_limit_flag() -> None:
    page = MagicMock(items=[], count=0)
    view = MagicMock()
    view.get_item.return_value = MagicMock(node_type="config")
    view.namespace_audit_timeline.return_value = page

    ctx = MagicMock()
    ctx.output = None
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    runner = CliRunner()
    result = runner.invoke(timeline_audit_cmd, ["app/web", "--limit", "5"], obj=ctx)
    assert result.exit_code == 0, result.output
    view.namespace_audit_timeline.assert_called_once_with(
        object_id="app/web",
        object_type="config",
        search=None,
        limit=5,
        offset=0,
    )
