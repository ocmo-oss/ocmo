"""Tests for ocmo apply config normalization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from ocmo_cli._config_content import prepare_config_apply_content
from ocmo_cli.commands.apply import apply_cmd
from ocmo_cli.main import cli


def test_apply_help_has_no_yes_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["apply", "--help"])
    assert result.exit_code == 0, result.output
    assert "  -y," not in result.output
    assert "--yes" not in result.output


def test_prepare_config_apply_content_converts_json_file() -> None:
    content = '{"replicas": 3, "image": "nginx"}'
    out = prepare_config_apply_content(content, source_name="app/web.json")
    assert out.startswith("_ocmo:")
    assert "replicas: 3" in out
    assert '"replicas"' not in out
    assert "format: json" in out


def test_prepare_config_apply_content_keeps_yaml_file() -> None:
    content = "replicas: 3\nimage: nginx\n"
    out = prepare_config_apply_content(content, source_name="app/web.yaml")
    assert out == content


def test_prepare_config_apply_content_converts_stdin_json() -> None:
    content = '{"enabled": true}'
    out = prepare_config_apply_content(content, source_name="<stdin>")
    assert "enabled: true" in out
    assert "_ocmo:" in out


def test_prepare_config_apply_content_keeps_stdin_yaml() -> None:
    content = "enabled: true\n"
    out = prepare_config_apply_content(content, source_name="<stdin>")
    assert out == content


def test_apply_uploads_yaml_for_json_config_file() -> None:
    view = MagicMock()
    view.update_config.side_effect = RuntimeError("missing")
    ns = MagicMock()
    ns.update_config = view.update_config
    ns.create_config = view.create_config

    ctx = MagicMock()
    ctx.namespace = "prod"
    ctx.dry_run = False
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = ns
    ctx.namespace_view.return_value = ns
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("app.json", "w") as f:
            f.write('{"replicas": 2}')
        with patch("ocmo_cli.commands.apply.status"):
            result = runner.invoke(
                apply_cmd,
                ["app/web", "-f", "app.json", "-n", "prod"],
                obj=ctx,
            )

    assert result.exit_code == 0, result.output
    _, kwargs = ns.create_config.call_args
    uploaded = kwargs["content"]
    assert "replicas: 2" in uploaded
    assert '"replicas"' not in uploaded
    assert "format: json" in uploaded
