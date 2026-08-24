"""Tests for ``ocmo import``."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._import_metadata import (
    read_file_metadata,
    strip_export_metadata_comments,
    strip_leading_metadata_comments,
)
from ocmo_cli._import_plan import classify_file_kind, try_parse_config_document
from ocmo_cli.commands.import_ import (
    _config_document_body,
    _expected_verify_rel,
    import_cmd,
)
from ocmo_cli.main import cli


def test_import_help_has_from_metadata_without_with_manifest() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["import", "--help"])
    assert result.exit_code == 0, result.output
    assert "--from-metadata" in result.output
    assert "--type-override" in result.output
    assert "--type-map" in result.output
    assert "--template-suffix" not in result.output
    assert "--with-manifest" not in result.output


def test_classify_file_kind_by_content_not_extension() -> None:
    assert classify_file_kind(b"replicas: 3\n") == "config"
    assert classify_file_kind(b'{"replicas": 3}\n') == "config"
    assert classify_file_kind(b"server {\n  listen 80;\n}\n") == "template"


def test_try_parse_config_document_detects_json() -> None:
    doc, is_json = try_parse_config_document(b'{"a": 1}')
    assert doc == {"a": 1}
    assert is_json is True


def test_read_file_metadata_from_yaml_comments(tmp_path: Path) -> None:
    path = tmp_path / "web"
    path.write_text("# namespace: prod\n" "# path: app/web\n" "# node_type: config\n" "key: value\n")
    meta = read_file_metadata(path)
    assert meta["namespace"] == "prod"
    assert meta["path"] == "app/web"
    assert meta["node_type"] == "config"


def test_strip_leading_metadata_comments_for_template() -> None:
    content = "{# namespace: prod #}\n" "{# path: app/site.conf #}\n" "server {\n}\n"
    assert strip_export_metadata_comments(content) == "server {\n}\n"
    assert strip_leading_metadata_comments(content, node_type="template") == "server {\n}\n"


def test_strip_export_metadata_comments_keeps_ocmo_name_header() -> None:
    content = "# ocmo.name: nginx/site.conf\n" "{% raw %}server {}\n{% endraw %}"
    assert strip_export_metadata_comments(content) == content


def test_strip_export_metadata_comments_strips_yaml_export_headers() -> None:
    content = "# namespace: prod\n" "# path: app/web\n" "# node_type: config\n" "key: value\n"
    assert strip_export_metadata_comments(content) == "key: value\n"


def test_import_config_strips_export_metadata_comments(tmp_path: Path) -> None:
    (tmp_path / "web.yaml").write_text("# namespace: prod\n" "# path: app/web\n" "# node_type: config\n" "key: value\n")

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")
    view.update_config.side_effect = RuntimeError("not found")

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(tmp_path), "--to=app/", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    content = view.create_config.call_args.kwargs["content"]
    assert "# namespace:" not in content
    assert "# path:" not in content
    assert "key: value\n" in content


@pytest.mark.skipif(not hasattr(os, "setxattr"), reason="xattr not supported")
def test_read_file_metadata_prefers_xattrs(tmp_path: Path) -> None:
    path = tmp_path / "db"
    path.write_text("# path: ignored\nsecret: true\n")
    try:
        os.setxattr(path, "user.ocmo.path", b"app/db")
        os.setxattr(path, "user.ocmo.node_type", b"secret")
    except OSError:
        pytest.skip("xattr not supported on this filesystem")

    meta = read_file_metadata(path)
    assert meta["path"] == "app/db"
    assert meta["node_type"] == "secret"


def test_import_dry_run_prints_kubectl_style_table(tmp_path: Path) -> None:
    (tmp_path / "web.yaml").write_text("key: value\n")
    (tmp_path / "nginx.conf").write_text("server {}\n")

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(tmp_path), "--to=app/", "--dry-run"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "SOURCE" in result.output
    assert "TYPE" in result.output
    assert "PATH" in result.output
    assert "ACTION" in result.output
    assert "STATUS" in result.output
    assert "web.yaml" in result.output
    assert "nginx.conf" in result.output
    assert "config" in result.output
    assert "template" in result.output


def test_import_dry_run_fails_on_existing_item_without_update(tmp_path: Path) -> None:
    (tmp_path / "web.yaml").write_text("key: value\n")

    view = MagicMock()
    view.get_item.return_value = object()

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(tmp_path), "--to=app/", "--dry-run"],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "Import blocked by conflicts" in result.output
    assert "already exists" in result.output


def test_import_from_metadata_uses_path_and_optional_to_prefix(tmp_path: Path) -> None:
    exported = tmp_path / "web"
    exported.write_text("# namespace: prod\n" "# path: app/web\n" "# node_type: config\n" "key: value\n")

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")
    view.update_config.side_effect = RuntimeError("not found")

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(tmp_path), "--from-metadata", "--to=backup", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.create_config.assert_called_once()
    assert view.create_config.call_args.kwargs["path"] == "backup/app/web"
    assert "key: value" in view.create_config.call_args.kwargs["content"]


def test_import_from_metadata_preserves_ocmo_block(tmp_path: Path) -> None:
    exported = tmp_path / "web"
    exported.write_text(
        "# namespace: prod\n"
        "# path: app/web\n"
        "# node_type: config\n"
        "_ocmo:\n"
        "  name: original.conf\n"
        "key: value\n"
    )

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")
    view.update_config.side_effect = RuntimeError("not found")

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(tmp_path), "--from-metadata", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    content = view.create_config.call_args.kwargs["content"]
    assert "_ocmo:\n  name: original.conf\n" in content
    assert "key: value\n" in content


def test_import_type_override_cli_forces_template(tmp_path: Path) -> None:
    (tmp_path / "values.yaml").write_text("replicas: 3\n")

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [
            str(tmp_path),
            "--to=app/",
            "--dry-run",
            "--type-override=values.yaml=template",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "values.yaml" in result.output
    assert "template" in result.output
    assert "app/values.yaml" in result.output
    assert "app/values.yaml.template" not in result.output


def test_import_non_yaml_file_imports_as_direct_template(tmp_path: Path) -> None:
    (tmp_path / "nginx.conf").write_text("server {}\n")

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")
    view.update_template.side_effect = RuntimeError("not found")

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(tmp_path), "--to=app/", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.create_template.assert_called_once()
    view.create_config.assert_not_called()
    assert view.create_template.call_args.kwargs["path"] == "app/nginx.conf"
    assert view.create_template.call_args.kwargs["content"] == "server {}\n"


def test_import_type_map_file_overrides_classification(tmp_path: Path) -> None:
    (tmp_path / "site.conf").write_text("server {}\n")
    type_map = tmp_path / "types.yaml"
    type_map.write_text('"*.conf": config\n')

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [
            str(tmp_path),
            "--to=app/",
            "--dry-run",
            f"--type-map={type_map}",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "site.conf" in result.output
    assert "config" in result.output


def test_import_from_metadata_type_override_beats_metadata_node_type(tmp_path: Path) -> None:
    exported = tmp_path / "db"
    exported.write_text("# path: app/db\n" "# node_type: config\n" "password: s3cr3t\n")

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")
    view.update_secret.side_effect = RuntimeError("not found")

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [
            str(tmp_path),
            "--from-metadata",
            "--yes",
            "--type-override=db=secret",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.create_secret.assert_called_once()
    assert view.create_secret.call_args.kwargs["path"] == "app/db"


def test_import_requires_to_without_from_metadata(tmp_path: Path) -> None:
    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(tmp_path), "--yes"],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "--to is required" in result.output


def test_expected_verify_rel_uses_tree_path_under_target_prefix() -> None:
    entry = {
        "kind": "config",
        "source_rel": Path("my.conf3"),
        "tree_path": "import-test/apply-test/my.conf3",
    }
    assert _expected_verify_rel(entry, "import-test/") == "apply-test/my.conf3"


def test_config_document_body_strips_ocmo_metadata() -> None:
    body = _config_document_body(
        {"_ocmo": {"cast": {"format": "json"}}, "test1": "value1"},
        "_ocmo",
    )
    assert body == {"test1": "value1"}


def test_import_verify_matches_config_data_without_ocmo_block(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "my.conf3").write_text(
        "# path: apply-test/my.conf3\n"
        "# node_type: config\n"
        "_ocmo:\n"
        "  cast:\n"
        "    format: json\n"
        "test1: value1\n"
        "test2: value2\n"
        "test3: true\n"
    )

    resolved_item = type(
        "ResolvedItem",
        (),
        {
            "name": "apply-test/my.conf3",
            "bytes": b'{"test1": "value1", "test2": "value2", "test3": true}\n',
        },
    )()

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")
    view.update_config.side_effect = RuntimeError("not found")
    view.resolve.return_value = iter([resolved_item])

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(source), "--to=import-test/", "--from-metadata", "--verify", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "Verification passed." in result.output


def test_import_verify_skips_standalone_templates(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "my.template").write_text(
        "# path: apply-test/my.template\n" "# node_type: template\n" '{"test1": "value1"}\n'
    )

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")
    view.update_template.side_effect = RuntimeError("not found")
    view.resolve.return_value = iter([])

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(source), "--to=import-test/", "--from-metadata", "--verify", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "Verification passed." in result.output


def test_import_verify_writes_resolved_output(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "web.yaml").write_text("key: value\n")

    resolved_item = type(
        "ResolvedItem",
        (),
        {"name": "web.yaml", "bytes": b"key: value\n"},
    )()

    view = MagicMock()
    view.get_item.side_effect = RuntimeError("not found")
    view.update_config.side_effect = RuntimeError("not found")
    view.resolve.return_value = iter([resolved_item])

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.dry_run = False
    ctx.yes = True
    ctx.client.return_value.version.return_value = MagicMock(
        to_dict=lambda: {"config_metadata_key": "_ocmo"},
    )

    runner = CliRunner()
    result = runner.invoke(
        import_cmd,
        [str(source), "--to=app/", "--verify", "--yes"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    view.resolve.assert_called_once_with("app/")
    assert "Verification passed." in result.output
