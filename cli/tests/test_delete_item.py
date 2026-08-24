"""Tests for ``ocmo delete item`` preview flag and output."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner
from ocmo._generated.models.delete_schema import DeleteSchema

from ocmo_cli._delete_item_output import (
    delete_item_table_columns,
    delete_item_table_rows,
    is_folder_delete,
    parse_delete_preview_line,
    parse_delete_preview_lines,
)
from ocmo_cli.commands.generated import _execute_generated
from ocmo_cli.main import cli


def test_parse_delete_preview_line_tree_items() -> None:
    assert parse_delete_preview_line("my-first-namespace:: Folder:: test/empty/soempty") == {
        "path": "test/empty/soempty",
        "name": "soempty",
        "node_type": "folder",
    }
    assert parse_delete_preview_line("prod:: Config:: app/api") == {
        "path": "app/api",
        "name": "api",
        "node_type": "config",
    }
    assert parse_delete_preview_line("prod:: Secret:: creds/db") == {
        "path": "creds/db",
        "name": "db",
        "node_type": "secret",
    }


def test_parse_delete_preview_line_splits_version_suffix() -> None:
    assert parse_delete_preview_line("prod:: Config:: app/api@3") == {
        "path": "app/api",
        "name": "api",
        "node_type": "config",
        "version": 3,
    }


def test_parse_delete_preview_line_unknown_format_fallback() -> None:
    assert parse_delete_preview_line("app/api") == {
        "path": "app/api",
        "name": "api",
        "node_type": "config",
    }


def test_is_folder_delete_matches_target_path() -> None:
    entries = parse_delete_preview_lines(
        [
            "prod:: Folder:: app",
            "prod:: Config:: app/api",
        ]
    )
    assert is_folder_delete(entries, "app")
    assert is_folder_delete(entries, "app/")
    assert not is_folder_delete(entries, "app/api")


def test_delete_item_help_has_preview_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "item", "--help"])
    assert result.exit_code == 0, result.output
    assert "--preview" in result.output


def test_execute_generated_delete_item_passes_version_tag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = True
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.delete_item.return_value = DeleteSchema(delete=["prod:: Config:: app/api@2"])

    _execute_generated(
        ctx=ctx,
        op_ids=["delete_item"],
        action="delete",
        resource="item",
        address="app/api@stable",
        namespace="prod",
        output_fmt="table",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode="destructive",
    )

    view.delete_item.assert_called_once_with(path="app/api", version="stable", preview=False)
    captured = capsys.readouterr()
    assert "app/api" in captured.out
    assert "2" in captured.out
    assert "config" in captured.out


def test_delete_item_table_rows_include_version_column_for_version_delete() -> None:
    entries = parse_delete_preview_lines(["prod:: Config:: app/api@2"])
    rows = delete_item_table_rows(entries)
    assert rows == [{"type": "config", "path": "app/api", "version": 2}]
    assert delete_item_table_columns(rows) == ["type", "version", "path"]


def test_delete_item_table_rows_omit_version_column_for_whole_item_delete() -> None:
    entries = parse_delete_preview_lines(["prod:: Config:: app/api"])
    rows = delete_item_table_rows(entries)
    assert rows == [{"type": "config", "path": "app/api"}]
    assert delete_item_table_columns(rows) == ["type", "path"]


def test_format_delete_item_dry_run_with_tag() -> None:
    from ocmo_cli._dry_run import format_generated_dry_run

    lines = format_generated_dry_run(
        op_id="delete_item",
        action="delete",
        resource="item",
        path="app/web",
        version="stable",
        namespace="prod",
        args=["app/web"],
        kwargs={"version": "stable"},
        client_scope=False,
    )
    assert lines == [
        "Would delete version 'stable' of item 'app/web' in namespace 'prod' " "(not the item itself).",
    ]


def test_execute_generated_delete_item_passes_preview_false(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = True
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.delete_item.return_value = DeleteSchema(delete=["prod:: Config:: app/api"])

    _execute_generated(
        ctx=ctx,
        op_ids=["delete_item"],
        action="delete",
        resource="item",
        address="app/api",
        namespace="prod",
        output_fmt="table",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode="destructive",
    )

    view.delete_item.assert_called_once_with(path="app/api", preview=False)
    captured = capsys.readouterr()
    assert "app/api" in captured.out
    assert "config" in captured.out


def test_execute_generated_delete_item_preview_passes_true(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = False
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.delete_item.return_value = DeleteSchema(
        delete=[
            "prod:: Folder:: app",
            "prod:: Config:: app/api",
        ]
    )

    _execute_generated(
        ctx=ctx,
        op_ids=["delete_item"],
        action="delete",
        resource="item",
        address="app/",
        namespace="prod",
        output_fmt="table",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=False,
        file_path=None,
        confirm_mode="destructive",
        sdk_extra={"preview": True},
    )

    view.delete_item.assert_called_once_with(path="app/", preview=True)
    captured = capsys.readouterr()
    assert "├── " in captured.out or "└── " in captured.out
    assert "app" in captured.out
    assert "[folder]" in captured.out
    assert "api" in captured.out


def test_execute_generated_delete_item_confirm_message_for_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []

    def fake_confirm(message: str, *, yes: bool = False) -> bool:
        prompts.append(message)
        return False

    monkeypatch.setattr("ocmo_cli._output.confirm", fake_confirm)

    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = False
    ctx.no_color = True

    with pytest.raises(SystemExit) as exc_info:
        _execute_generated(
            ctx=ctx,
            op_ids=["delete_item"],
            action="delete",
            resource="item",
            address="audit-test/new.conf@17",
            namespace="prod",
            output_fmt="table",
            field=None,
            version_flag=None,
            dry_run=False,
            yes=False,
            file_path=None,
            confirm_mode="destructive",
        )

    assert exc_info.value.code == 0
    assert prompts == [
        "This will delete version 17 for item 'audit-test/new.conf'. Continue?",
    ]


def test_execute_generated_delete_item_preview_skips_confirm() -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = False
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.delete_item.return_value = DeleteSchema(delete=["prod:: Config:: app/api"])

    _execute_generated(
        ctx=ctx,
        op_ids=["delete_item"],
        action="delete",
        resource="item",
        address="app/api",
        namespace="prod",
        output_fmt="name",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=False,
        file_path=None,
        confirm_mode="destructive",
        sdk_extra={"preview": True},
    )

    view.delete_item.assert_called_once_with(path="app/api", preview=True)
