"""Tests for version/tag addressing on ocmo get item."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ocmo_cli.commands.generated import _execute_generated


def test_get_item_address_suffix_passes_version(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"

    _execute_generated(
        ctx=ctx,
        op_ids=["get_item"],
        action="get",
        resource="item",
        address="apply-test/my.conf@2",
        namespace="prod",
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Would get item 'apply-test/my.conf'@2 in namespace 'prod'." in captured.err


def test_get_item_version_flag_passes_version(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"

    _execute_generated(
        ctx=ctx,
        op_ids=["get_item"],
        action="get",
        resource="item",
        address="apply-test/my.conf",
        namespace="prod",
        output_fmt=None,
        field=None,
        version_flag="stable",
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Would get item 'apply-test/my.conf'@stable in namespace 'prod'." in captured.err
