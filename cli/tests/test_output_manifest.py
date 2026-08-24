"""Tests for output format manifest."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from ocmo_cli._output_manifest import get_command_spec
from ocmo_cli.main import cli


def test_search_tree_spec_excludes_wide() -> None:
    spec = get_command_spec("search tree")
    assert "table" in spec.supported_formats
    assert "wide" not in spec.supported_formats
    assert spec.name_field == "path"


def test_get_namespace_spec_excludes_path_and_raw() -> None:
    spec = get_command_spec("get namespace")
    assert "table" in spec.supported_formats
    assert "wide" in spec.supported_formats
    assert "path" not in spec.supported_formats
    assert "raw" not in spec.supported_formats
    assert spec.table is not None
    assert spec.table.fields == ["name", "description"]


def test_get_audit_table_and_wide_columns() -> None:
    spec = get_command_spec("get audit")
    assert spec.table is not None
    assert spec.table.fields == ["occurred_at", "id", "operation", "object_id"]
    assert spec.wide is not None
    assert spec.wide.fields == [
        "occurred_at",
        "id",
        "operation",
        "object_id",
        "auth_email",
        "object_type",
        "object_version",
        "error",
    ]
    assert spec.name_field == "id"
    assert "namespace" not in spec.wide.fields


def test_ls_spec_includes_path() -> None:
    spec = get_command_spec("ls")
    assert "path" in spec.supported_formats
    assert "raw" not in spec.supported_formats


def test_resolve_spec_defaults_to_raw() -> None:
    spec = get_command_spec("resolve")
    assert spec.fixed_default == "raw"
    assert "raw" in spec.supported_formats


def test_resolve_parameters_spec_defaults_to_table() -> None:
    spec = get_command_spec("resolve parameters")
    assert spec.default_tty == "table"
    assert spec.default_non_tty == "yaml"
    assert "table" in spec.supported_formats
    assert "raw" not in spec.supported_formats


def test_create_config_spec_uses_document_profile() -> None:
    spec = get_command_spec("create config")
    assert spec.fixed_default == "raw"
    assert "raw" in spec.supported_formats
    assert "table" not in spec.supported_formats


@pytest.mark.parametrize(
    "command_key",
    [
        "update config",
        "update template",
        "update secret",
        "update resolver",
        "update globalpermission",
    ],
)
def test_update_document_commands_match_create_profile(command_key: str) -> None:
    spec = get_command_spec(command_key)
    create_key = command_key.replace("update", "create", 1)
    create_spec = get_command_spec(create_key)
    assert spec.fixed_default == create_spec.fixed_default
    assert spec.supported_formats == create_spec.supported_formats


@pytest.mark.parametrize("fmt", ("path", "raw"))
def test_get_namespace_cli_rejects_unsupported_formats(fmt: str) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "namespace", "-o", fmt])
    assert result.exit_code != 0
    assert "not a valid output format" in result.output


def test_delete_item_spec_excludes_wide_and_supports_path() -> None:
    spec = get_command_spec("delete item")
    assert "table" in spec.supported_formats
    assert "path" in spec.supported_formats
    assert "name" in spec.supported_formats
    assert "wide" not in spec.supported_formats
    assert spec.name_field == "path"
    assert spec.table is not None
    assert spec.table.fields == ["type", "version", "path"]


def test_delete_item_cli_rejects_wide_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "item", "-o", "wide"])
    assert result.exit_code != 0
    assert "not a valid output format" in result.output


def test_search_tree_cli_rejects_wide_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "tree", "-o", "wide"])
    assert result.exit_code != 0
    assert "not a valid output format" in result.output


def test_all_generated_commands_have_manifest_specs() -> None:
    from ocmo_cli._commands_map import OPERATIONS

    for op_id, config in OPERATIONS.items():
        if not isinstance(config, dict) or config.get("hand_written") or config.get("skip"):
            continue
        action = config.get("action")
        resource = config.get("resource")
        if not action or not resource:
            continue
        key = f"{action} {resource}"
        spec = get_command_spec(key)
        assert spec.supported_formats, f"empty formats for {key} ({op_id})"


def test_get_lock_help_mentions_jsonpath_once() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "lock", "--help"])
    assert result.exit_code == 0, result.output
    assert result.output.count("jsonpath") == 1
    assert "jsonpath=<path>" in result.output
    assert ", jsonpath," not in result.output
