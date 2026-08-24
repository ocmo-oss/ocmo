"""Tests for ``ocmo export``."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._dry_run import format_export_dry_run
from ocmo_cli.commands.export import export_cmd
from ocmo_cli.main import cli


def test_export_help_has_reveal_secrets_without_include_secrets_or_manifest() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--help"])
    assert result.exit_code == 0, result.output
    assert "--reveal-secrets" in result.output
    assert "--metadata" in result.output
    assert "--include-secrets" not in result.output
    assert "--manifest" not in result.output


def test_format_export_dry_run_places_namespace_before_destination() -> None:
    message = format_export_dry_run(
        item_path="app/web",
        dest_file="./backup/app/web",
        namespace="prod",
    )
    assert message == ("Would export 'app/web' from namespace 'prod' to './backup/app/web'.")


def test_export_writes_item_body_to_file(tmp_path: Path) -> None:
    view = MagicMock()
    view.navigate_path.return_value = {
        "children": [
            {"path": "app/web", "node_type": "config"},
        ],
    }
    view.get_item.return_value = SimpleNamespace(
        node_type="config",
        version_data=SimpleNamespace(data="key: value\n"),
    )

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True

    dest = tmp_path / "backup"
    runner = CliRunner()
    result = runner.invoke(
        export_cmd,
        ["app/", f"--to={dest}", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.get_item.assert_called_once_with(path="app/web", version="latest")
    assert (dest / "web").read_text() == "key: value\n"


def test_export_metadata_writes_yaml_comments_for_config(tmp_path: Path) -> None:
    view = MagicMock()
    view.navigate_path.return_value = {
        "children": [
            {"path": "app/web", "node_type": "config"},
        ],
    }
    view.get_item.return_value = SimpleNamespace(
        name="web",
        path="app/web",
        node_type="config",
        author="alice",
        description="",
        version_data=SimpleNamespace(
            version=1,
            data="key: value\n",
            updater="alice",
            updated_at="2026-01-01T00:00:00+00:00",
            deleted_at=None,
        ),
    )

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True

    dest = tmp_path / "backup"
    runner = CliRunner()
    result = runner.invoke(
        export_cmd,
        ["app/", f"--to={dest}", "--yes", "--metadata"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    text = (dest / "web").read_text()
    assert text.startswith("# namespace: prod\n# path: app/web\n")
    assert text.endswith("key: value\n")


def test_export_metadata_writes_jinja_comments_for_template(tmp_path: Path) -> None:
    view = MagicMock()
    view.navigate_path.return_value = {
        "children": [
            {"path": "app/site.conf", "node_type": "template"},
        ],
    }
    view.get_item.return_value = SimpleNamespace(
        name="site.conf",
        path="app/site.conf",
        node_type="template",
        author="alice",
        description="",
        version_data=SimpleNamespace(
            version=2,
            data="server {\n}\n",
            updater="alice",
            updated_at="2026-01-01T00:00:00+00:00",
            deleted_at=None,
        ),
    )

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True

    dest = tmp_path / "backup"
    runner = CliRunner()
    result = runner.invoke(
        export_cmd,
        ["app/", f"--to={dest}", "--yes", "--metadata"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    text = (dest / "site.conf").read_text()
    assert text.startswith("{# namespace: prod #}\n{# path: app/site.conf #}\n")
    assert "server {\n}" in text


def test_export_metadata_secret_has_no_comments_but_sets_xattrs(
    tmp_path: Path,
) -> None:
    import os

    if not hasattr(os, "setxattr"):
        pytest.skip("xattr not supported")

    view = MagicMock()
    view.navigate_path.return_value = {
        "children": [
            {"path": "app/db", "node_type": "secret"},
        ],
    }
    view.get_item.return_value = SimpleNamespace(
        name="db",
        path="app/db",
        node_type="secret",
        author="alice",
        description="",
        version_data=SimpleNamespace(
            version=1,
            data="password: s3cr3t\n",
            updater="alice",
            updated_at="2026-01-01T00:00:00+00:00",
            deleted_at=None,
        ),
    )

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True

    dest = tmp_path / "backup"
    runner = CliRunner()
    result = runner.invoke(
        export_cmd,
        ["app/", f"--to={dest}", "--reveal-secrets", "--yes", "--metadata"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    secret_file = dest / "db"
    assert secret_file.read_text() == "password: s3cr3t\n"
    try:
        assert os.getxattr(secret_file, "user.ocmo.namespace") == b"prod"
        assert os.getxattr(secret_file, "user.ocmo.path") == b"app/db"
        assert os.getxattr(secret_file, "user.ocmo.node_type") == b"secret"
    except OSError:
        pytest.skip("xattr not supported on this filesystem")


def test_export_reveal_secrets_includes_secret_items(tmp_path: Path) -> None:
    view = MagicMock()
    view.navigate_path.return_value = {
        "children": [
            {"path": "app/db", "node_type": "secret"},
        ],
    }
    view.get_item.return_value = SimpleNamespace(
        node_type="secret",
        version_data=SimpleNamespace(data="password: s3cr3t\n"),
    )

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True

    dest = tmp_path / "backup"
    runner = CliRunner()
    result = runner.invoke(
        export_cmd,
        ["app/", f"--to={dest}", "--reveal-secrets", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.get_item.assert_called_once_with(
        path="app/db",
        version="latest",
        reveal=True,
    )
    assert (dest / "db").read_text() == "password: s3cr3t\n"


def test_export_skips_secrets_by_default(tmp_path: Path) -> None:
    view = MagicMock()
    view.navigate_path.return_value = {
        "children": [
            {"path": "app/db", "node_type": "secret"},
            {"path": "app/web", "node_type": "config"},
        ],
    }
    view.get_item.return_value = SimpleNamespace(
        node_type="config",
        version_data=SimpleNamespace(data="x: 1\n"),
    )

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True

    dest = tmp_path / "backup"
    runner = CliRunner()
    result = runner.invoke(
        export_cmd,
        ["app/", f"--to={dest}", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.get_item.assert_called_once_with(path="app/web", version="latest")
    assert (dest / "web").exists()
    assert not (dest / "db").exists()
