"""Tests for ocmo edit command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ocmo_cli._exit import USAGE_ERROR
from ocmo_cli._output_manifest import get_command_spec
from ocmo_cli.commands.edit import _run_edit
from ocmo_cli.main import cli


def _config_item(*, data: str = "replicas: 3\n", deleted_at: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        name="web",
        path="app/web",
        node_type="config",
        author="alice",
        description="",
        tags=SimpleNamespace(to_dict=lambda: {}),
        version_data=SimpleNamespace(
            version=2,
            tags=[],
            data=data,
            updater="bob",
            updated_at="2026-02-15T10:30:00+00:00",
            deleted_at=deleted_at,
            to_dict=lambda: {
                "version": 2,
                "tags": [],
                "data": data,
                "updater": "bob",
                "updated_at": "2026-02-15T10:30:00+00:00",
                "deleted_at": deleted_at,
            },
        ),
        to_dict=lambda: {
            "name": "web",
            "path": "app/web",
            "node_type": "config",
        },
    )


def test_edit_config_spec_uses_document_profile() -> None:
    spec = get_command_spec("edit config")
    update_spec = get_command_spec("update config")
    assert spec.fixed_default == update_spec.fixed_default
    assert spec.supported_formats == update_spec.supported_formats


def test_edit_help_lists_aliases_on_one_line() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "--help"])
    assert result.exit_code == 0, result.output
    assert "config" in result.output
    assert "aliases: cfg, configs" in result.output


def test_edit_config_help_has_output_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["edit", "config", "--help"])
    assert result.exit_code == 0, result.output
    assert "--output" in result.output or "  -o," in result.output


def test_run_edit_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.dry_run = True
    ctx.require_namespace.return_value = "prod"

    _run_edit(
        ctx=ctx,
        resource="config",
        address="app/web",
        namespace="prod",
        output_fmt=None,
        version_flag=None,
    )

    captured = capsys.readouterr()
    assert "Would edit config 'app/web' via $EDITOR in namespace 'prod'." in captured.err


def test_run_edit_no_changes(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.output = None
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.get_item.return_value = _config_item()

    monkeypatch.setattr(
        "ocmo_cli.commands.edit._edit_in_temp_file",
        lambda content, editor, suffix=".yaml": content,
    )

    _run_edit(
        ctx=ctx,
        resource="config",
        address="app/web",
        namespace="prod",
        output_fmt=None,
        version_flag=None,
    )

    captured = capsys.readouterr()
    assert captured.out == "No changes.\n"
    view.update_config.assert_not_called()


def test_run_edit_updates_and_emits_raw_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.output = None
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.get_item.return_value = _config_item(data="replicas: 3\n")
    view.update_config.return_value = _config_item(data="replicas: 5\n")

    monkeypatch.setattr(
        "ocmo_cli.commands.edit._edit_in_temp_file",
        lambda content, editor, suffix=".yaml": "replicas: 5\n",
    )

    _run_edit(
        ctx=ctx,
        resource="config",
        address="app/web",
        namespace="prod",
        output_fmt=None,
        version_flag=None,
    )

    captured = capsys.readouterr()
    assert captured.out == "replicas: 5\n"
    assert "# path: app/web" in captured.err
    assert "Updated config 'app/web'." in captured.err
    view.update_config.assert_called_once_with(path="app/web", content="replicas: 5\n")


def test_run_edit_secret_requests_reveal() -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.output = None
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.get_item.return_value = SimpleNamespace(
        node_type="secret",
        path="app/db",
        version_data=SimpleNamespace(data="secret-value\n"),
    )

    with patch("ocmo_cli.commands.edit._edit_in_secure_temp", return_value="secret-value\n"):
        _run_edit(
            ctx=ctx,
            resource="secret",
            address="app/db",
            namespace="prod",
            output_fmt=None,
            version_flag=None,
        )

    view.get_item.assert_called_once_with(path="app/db", reveal=True)


def test_run_edit_rejects_deleted_version(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.output = None
    ctx.no_color = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.get_item.return_value = _config_item(
        data="",
        deleted_at="2026-02-15T10:30:00+00:00",
    )

    monkeypatch.setattr(
        "ocmo_cli.commands.edit._edit_in_temp_file",
        lambda content, editor, suffix=".yaml": content,
    )

    with pytest.raises(SystemExit) as exc:
        _run_edit(
            ctx=ctx,
            resource="config",
            address="app/web@2",
            namespace="prod",
            output_fmt=None,
            version_flag=None,
        )

    assert exc.value.code == USAGE_ERROR
    captured = capsys.readouterr()
    assert "Cannot edit deleted version 2 of 'app/web'." in captured.err
    view.update_config.assert_not_called()
