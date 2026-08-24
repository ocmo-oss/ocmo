"""Tests for generated command groups."""

from __future__ import annotations

from click.testing import CliRunner

from ocmo_cli._exit import USAGE_ERROR
from ocmo_cli.main import cli
from tests.helpers import assert_help_excludes_io_flags


def test_create_help_lists_aliases_on_one_line() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "--help"])
    assert result.exit_code == 0, result.output
    assert "config" in result.output
    assert "aliases: cfg, configs" in result.output
    for line in result.output.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("cfg ") or stripped.startswith("configs "):
            raise AssertionError(f"alias listed as separate command: {line!r}")


def test_create_alias_still_works() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "cfg", "--help"])
    assert result.exit_code == 0, result.output


def test_create_namespace_help_has_no_namespace_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "namespace", "--help"])
    assert result.exit_code == 0, result.output
    assert "--namespace" not in result.output
    assert "  -n," not in result.output


def test_create_gp_help_has_no_namespace_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "gp", "--help"])
    assert result.exit_code == 0, result.output
    assert "--namespace" not in result.output
    assert "  -n," not in result.output


def test_get_namespace_help_mentions_list_not_description() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "namespace", "--help"])
    assert result.exit_code == 0, result.output
    assert "--description" not in result.output
    assert "list all" in result.output.lower()


def test_get_namespace_help_has_no_namespace_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "namespace", "--help"])
    assert result.exit_code == 0, result.output
    assert "--namespace" not in result.output
    assert "  -n," not in result.output


def test_get_gp_help_has_no_namespace_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "gp", "--help"])
    assert result.exit_code == 0, result.output
    assert "--namespace" not in result.output
    assert "  -n," not in result.output


def test_get_audit_help_keeps_namespace_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "audit", "--help"])
    assert result.exit_code == 0, result.output
    assert "--namespace" in result.output


def test_get_namespace_rejects_explicit_global_namespace_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-n", "prod", "get", "namespace"], catch_exceptions=False)
    assert result.exit_code == USAGE_ERROR
    assert "not valid for this command" in result.output


def test_create_namespace_help_mentions_description() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "namespace", "--help"])
    assert result.exit_code == 0, result.output
    assert "--description" in result.output


def test_create_config_help_has_no_yes_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "config", "--help"])
    assert result.exit_code == 0, result.output
    assert "  -y," not in result.output
    assert "--yes" not in result.output


def test_update_config_help_has_file_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["update", "config", "--help"])
    assert result.exit_code == 0, result.output
    assert "  -f," in result.output or "--file" in result.output


def test_update_config_help_has_no_yes_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["update", "config", "--help"])
    assert result.exit_code == 0, result.output
    assert "  -y," not in result.output
    assert "--yes" not in result.output


def test_update_lock_help_matches_create_lock_flags() -> None:
    runner = CliRunner()
    create = runner.invoke(cli, ["create", "lock", "--help"])
    update = runner.invoke(cli, ["update", "lock", "--help"])
    assert create.exit_code == 0, create.output
    assert update.exit_code == 0, update.output
    for result in (create, update):
        assert "--reason" in result.output
        assert "--expires-at" in result.output
        assert "  -f," not in result.output
        assert "  --file" not in result.output


def test_replace_command_group_removed() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["replace", "--help"])
    assert result.exit_code != 0


def test_delete_item_help_has_yes_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "item", "--help"])
    assert result.exit_code == 0, result.output
    assert "  -y," in result.output
    assert "--yes" in result.output


def test_get_version_requires_address() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "version"])
    assert result.exit_code == USAGE_ERROR
    assert "Missing argument 'ADDRESS'" in result.output


def test_get_version_help_shows_required_address() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "version", "--help"])
    assert result.exit_code == 0, result.output
    assert "ADDRESS" in result.output
    assert "@version" in result.output or "@tag" in result.output


def test_delete_subcommands_help_have_no_file_flag() -> None:
    runner = CliRunner()
    for resource in ("namespace", "item", "globalpermission", "lock"):
        result = runner.invoke(cli, ["delete", resource, "--help"])
        assert result.exit_code == 0, result.output
        assert "  -f," not in result.output
        assert "  --file" not in result.output


def test_tag_and_untag_help_have_no_file_flag() -> None:
    runner = CliRunner()
    for cmd in ("tag", "untag"):
        result = runner.invoke(cli, [cmd, "item", "--help"])
        assert result.exit_code == 0, result.output
        assert "  -f," not in result.output
        assert "  --file" not in result.output


def test_propagate_config_help_has_no_file_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["propagate", "config", "--help"])
    assert result.exit_code == 0, result.output
    assert "  -f," not in result.output
    assert "  --file" not in result.output


def test_tag_item_requires_tag_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-n", "prod", "tag", "item", "x/confT@2"])
    assert result.exit_code == USAGE_ERROR
    assert "Missing option '--tag'" in result.output


def test_untag_item_requires_tag_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-n", "prod", "untag", "item", "x/confT@2"])
    assert result.exit_code == USAGE_ERROR
    assert "Missing option '--tag'" in result.output


def test_rotate_help_describes_resolver_access_token() -> None:
    runner = CliRunner()
    group = runner.invoke(cli, ["rotate", "--help"])
    token = runner.invoke(cli, ["rotate", "token", "--help"])
    assert group.exit_code == 0, group.output
    assert token.exit_code == 0, token.output
    assert "resolver access token" in group.output.lower()
    assert "resolver access token" in token.output.lower()
    assert "secret" not in group.output.lower()
    assert "--token-number" in token.output
    assert_help_excludes_io_flags(token.output)
    assert "--field" not in token.output


def test_rotate_token_requires_token_number() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-n", "prod", "rotate", "token", "app/resolvers/svc"])
    assert result.exit_code != 0
    assert "Missing option '--token-number'" in result.output
