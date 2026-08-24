"""Tests for hand-written ``ocmo move item`` and ``ocmo copy item``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._exit import USAGE_ERROR
from ocmo_cli.commands.item_relocate import copy_item_cmd, move_item_cmd
from ocmo_cli.main import cli
from tests.helpers import assert_help_excludes_io_flags


def test_move_item_help_has_source_target_yes_and_no_output_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["move", "item", "--help"])
    assert result.exit_code == 0, result.output
    assert "SOURCE" in result.output
    assert "TARGET" in result.output
    assert "--yes" in result.output
    assert "--dry-run" in result.output
    assert_help_excludes_io_flags(result.output)


def test_copy_item_help_has_source_target_yes_and_no_output_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["copy", "item", "--help"])
    assert result.exit_code == 0, result.output
    assert "SOURCE" in result.output
    assert "TARGET" in result.output
    assert "--yes" in result.output
    assert_help_excludes_io_flags(result.output)


def test_move_item_requires_source_and_target() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-n", "prod", "move", "item", "app/web"])
    assert result.exit_code == USAGE_ERROR
    assert "Missing argument 'TARGET'" in result.output


def test_move_item_rejects_version_on_source() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["-n", "prod", "move", "item", "app/web@stable", "app/archive/web"],
    )
    assert result.exit_code == USAGE_ERROR
    assert "does not support @version" in result.output


def test_move_item_rejects_version_on_target() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["-n", "prod", "move", "item", "app/web", "app/archive/web@2"],
    )
    assert result.exit_code == USAGE_ERROR
    assert "TARGET does not support @version" in result.output


def test_move_item_requires_yes_in_non_interactive_mode() -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = False

    runner = CliRunner()
    result = runner.invoke(
        move_item_cmd,
        ["app/web", "app/archive/web"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "use --yes to confirm" in result.output
    ctx.ns.assert_not_called()


def test_move_item_calls_sdk_with_source_and_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = MagicMock()
    view.move_item.return_value = {"path": "app/archive/web"}

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = True

    runner = CliRunner()
    result = runner.invoke(
        move_item_cmd,
        ["app/web", "app/archive/web"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.move_item.assert_called_once_with(
        "app/web",
        target_path="app/archive/web",
    )
    assert "Item 'app/web' was moved to 'app/archive/web'." in result.output


def test_copy_item_calls_sdk_with_tag_from_source_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = MagicMock()
    view.copy_item.return_value = {"items": []}

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = True

    runner = CliRunner()
    result = runner.invoke(
        copy_item_cmd,
        ["app/web@stable", "app/staging/web"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.copy_item.assert_called_once_with(
        "app/web",
        target_path="app/staging/web",
        tag_to_copy="stable",
    )
    assert "Item 'app/web' was copied to 'app/staging/web'." in result.output


def test_move_item_calls_sdk_with_directory_target() -> None:
    view = MagicMock()
    view.move_item.return_value = {"path": "a/d"}

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = True

    runner = CliRunner()
    result = runner.invoke(
        move_item_cmd,
        ["b/c/d", "a/"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.move_item.assert_called_once_with(
        "b/c/d",
        target_path="a/d",
    )
    assert "Item 'b/c/d' was moved to 'a/d'." in result.output


def test_copy_item_calls_sdk_with_directory_target() -> None:
    view = MagicMock()
    view.copy_item.return_value = {"items": []}

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = True

    runner = CliRunner()
    result = runner.invoke(
        copy_item_cmd,
        ["b/c/d", "a/"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.copy_item.assert_called_once_with(
        "b/c/d",
        target_path="a/d",
    )
    assert "Item 'b/c/d' was copied to 'a/d'." in result.output


def test_move_item_dry_run_skips_confirmation() -> None:
    ctx = MagicMock()
    ctx.require_namespace.return_value = "my-first-namespace"
    ctx.dry_run = True
    ctx.output = None
    ctx.yes = False

    runner = CliRunner()
    result = runner.invoke(
        move_item_cmd,
        ["b/c/d", "a/", "--dry-run"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "Would move item 'b/c/d' to 'a/d'" in result.output
    assert "After move, item will be available at 'a/d'." in result.output
    assert "use --yes to confirm" not in result.output


def test_move_item_dry_run_mentions_source_and_target() -> None:
    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.dry_run = True
    ctx.output = None
    ctx.yes = False

    runner = CliRunner()
    result = runner.invoke(
        move_item_cmd,
        ["app/web", "app/archive/web", "--dry-run"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "Would move item 'app/web' to 'app/archive/web'" in result.output
    assert "After move, item will be available at 'app/archive/web'." in result.output
