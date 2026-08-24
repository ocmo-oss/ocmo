"""Tests for hand-written ``ocmo move globalpermission``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli.commands.gp_move import move_globalpermission_cmd
from ocmo_cli.main import cli
from tests.helpers import assert_help_excludes_io_flags

_RULE = {
    "id": "ead38b7a-515d-4bd3-afb4-99715746c858",
    "position": 4.0,
    "rule": {
        "id": "atatatata",
        "namespace": "dev-*",
        "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
    },
}


def test_move_globalpermission_help_has_position_yes_and_no_output_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["move", "globalpermission", "--help"])
    assert result.exit_code == 0, result.output
    assert "ADDRESS" in result.output
    assert "--position" in result.output
    assert "--yes" in result.output
    assert "--dry-run" in result.output
    assert_help_excludes_io_flags(result.output)
    assert "--field" not in result.output


def test_move_globalpermission_requires_position() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["move", "globalpermission", "dev-read"])
    assert result.exit_code != 0
    assert "Missing option '--position'" in result.output


def test_move_globalpermission_requires_yes_in_non_interactive_mode() -> None:
    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = False
    ctx.client.return_value = MagicMock()

    runner = CliRunner()
    result = runner.invoke(
        move_globalpermission_cmd,
        ["dev-read", "--position", "1.5"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "use --yes to confirm" in result.output
    ctx.client.return_value.move_global_permission.assert_not_called()


def test_move_globalpermission_dry_run_includes_position() -> None:
    ctx = MagicMock()
    ctx.dry_run = True
    ctx.yes = False

    runner = CliRunner()
    result = runner.invoke(
        move_globalpermission_cmd,
        ["dev-read", "--position", "1.5", "--dry-run"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    assert "Would move global permission rule 'dev-read' to position 1.5." in result.output
    ctx.client.assert_not_called()


def test_move_globalpermission_success_prints_get_globalpermission_output() -> None:
    client = MagicMock()
    client.move_global_permission.return_value = _RULE
    client.get_global_permission.return_value = _RULE

    ctx = MagicMock()
    ctx.dry_run = False
    ctx.yes = True
    ctx.output = None
    ctx.client.return_value = client

    runner = CliRunner()
    result = runner.invoke(
        move_globalpermission_cmd,
        ["atatatata", "--position", "4"],
        obj=ctx,
    )

    assert result.exit_code == 0, result.output
    client.move_global_permission.assert_called_once_with("atatatata", position=4.0)
    client.get_global_permission.assert_called_once_with("atatatata")
    assert "atatatata" in result.output
    assert "dev-*" in result.output


def test_emit_get_globalpermission_output_handles_sdk_objects(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from ocmo_cli._globalpermission_output import emit_get_globalpermission_output

    class _Rule:
        def to_dict(self) -> dict[str, object]:
            return _RULE

    emit_get_globalpermission_output(_Rule(), output_fmt="table")
    out = capsys.readouterr().out
    assert "atatatata" in out
    assert "dev-*" in out


def test_move_globalpermission_accepts_gp_alias() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["move", "gp", "--help"])
    assert result.exit_code == 0, result.output
    assert "--position" in result.output
