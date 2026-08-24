"""Tests for ``ocmo get audit`` address handling."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli.commands.generated import _execute_generated
from ocmo_cli.main import cli


def test_get_audit_help_mentions_event_id_prefix() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "audit", "--help"])
    assert result.exit_code == 0
    assert "hex prefix" in result.output.lower()


def test_execute_generated_get_audit_rejects_version_suffix() -> None:
    ctx = MagicMock()
    with pytest.raises(SystemExit):
        _execute_generated(
            ctx=ctx,
            op_ids=["get_namespace_audit_event", "list_namespace_audit"],
            action="get",
            resource="audit",
            address="550e8400@2",
            namespace="prod",
            output_fmt=None,
            field=None,
            version_flag=None,
            dry_run=True,
            yes=True,
            file_path=None,
            confirm_mode=None,
        )


def test_execute_generated_get_audit_show_passes_event_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_call_sdk_method(ctx, op_id, namespace, args, kwargs):
        captured["op_id"] = op_id
        captured["args"] = args
        return None

    monkeypatch.setattr(
        "ocmo_cli.commands.generated._call_sdk_method",
        fake_call_sdk_method,
    )

    ctx = MagicMock()
    ctx.output = None

    _execute_generated(
        ctx=ctx,
        op_ids=["get_namespace_audit_event", "list_namespace_audit"],
        action="get",
        resource="audit",
        address="a1b2c3d4",
        namespace="prod",
        output_fmt="yaml",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )

    assert captured["op_id"] == "get_namespace_audit_event"
    assert captured["args"] == ["a1b2c3d4"]
