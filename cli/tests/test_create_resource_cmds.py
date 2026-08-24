"""Tests for create namespace / gp / lock command wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ocmo_cli._exit import USAGE_ERROR
from ocmo_cli.commands.generated import _execute_generated


def test_create_namespace_dry_run_passes_body_only(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False

    _execute_generated(
        ctx=ctx,
        op_ids=["create_namespace"],
        action="create",
        resource="namespace",
        address="my-last-ns",
        namespace=None,
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )
    err = capsys.readouterr().err
    assert "Would create namespace 'my-last-ns'." in err
    assert "Would call" not in err


def test_create_namespace_dry_run_passes_description_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False

    _execute_generated(
        ctx=ctx,
        op_ids=["create_namespace"],
        action="create",
        resource="namespace",
        address="my-ns",
        namespace=None,
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"description": "My awesome NS"},
    )
    err = capsys.readouterr().err
    assert "Would create namespace 'my-ns'." in err
    assert "Description: 'My awesome NS'." in err


def test_create_global_permission_dry_run_passes_body_only(
    tmp_path: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body_file = tmp_path / "rule.yaml"  # type: ignore[operator]
    body_file.write_text('namespace: "dev/*"\nread:\n  allow: true\n')
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False

    _execute_generated(
        ctx=ctx,
        op_ids=["create_global_permission"],
        action="create",
        resource="globalpermission",
        address="dev-read",
        namespace=None,
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=str(body_file),
        confirm_mode=None,
    )
    err = capsys.readouterr().err
    assert "Would create global permission rule 'dev-read'" in err
    assert "rule.yaml" in err
    assert "Would call" not in err


def test_create_global_permission_dry_run_passes_position_flag(
    tmp_path: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body_file = tmp_path / "rule.yaml"  # type: ignore[operator]
    body_file.write_text('namespace: "dev/*"\nread:\n  allow: true\n')
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False

    _execute_generated(
        ctx=ctx,
        op_ids=["create_global_permission"],
        action="create",
        resource="globalpermission",
        address="dev-read",
        namespace=None,
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=str(body_file),
        confirm_mode=None,
        sdk_extra={"position": 1.5},
    )
    err = capsys.readouterr().err
    assert "Would create global permission rule 'dev-read'" in err
    assert "Would set rule position to 1.5." in err
    assert "move_global_permission" not in err
    assert "Would call" not in err


def test_create_lock_requires_reason_before_api(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = False
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"

    with pytest.raises(SystemExit) as exc:
        _execute_generated(
            ctx=ctx,
            op_ids=["create_lock"],
            action="create",
            resource="lock",
            address="app/web",
            namespace="prod",
            output_fmt=None,
            field=None,
            version_flag=None,
            dry_run=False,
            yes=True,
            file_path=None,
            confirm_mode=None,
        )
    assert exc.value.code == USAGE_ERROR
    assert "requires --reason" in capsys.readouterr().err


def test_create_lock_with_reason_flag_passes_body_dict(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"

    _execute_generated(
        ctx=ctx,
        op_ids=["create_lock"],
        action="create",
        resource="lock",
        address="app/web",
        namespace="prod",
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"reason": "deploy freeze"},
    )
    err = capsys.readouterr().err
    assert "Would create lock on 'app/web'" in err
    assert "deploy freeze" in err
    assert "Would call" not in err


def test_update_lock_requires_reason_before_api(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = False
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"

    with pytest.raises(SystemExit) as exc:
        _execute_generated(
            ctx=ctx,
            op_ids=["replace_lock"],
            action="update",
            resource="lock",
            address="app/web",
            namespace="prod",
            output_fmt=None,
            field=None,
            version_flag=None,
            dry_run=False,
            yes=True,
            file_path=None,
            confirm_mode=None,
        )
    assert exc.value.code == USAGE_ERROR
    assert "requires --reason" in capsys.readouterr().err


def test_update_lock_with_reason_flag_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"

    _execute_generated(
        ctx=ctx,
        op_ids=["replace_lock"],
        action="update",
        resource="lock",
        address="app/web",
        namespace="prod",
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
        sdk_extra={"reason": "extended freeze", "expires_at": "2026-12-31T00:00:00Z"},
    )
    err = capsys.readouterr().err
    assert "Would update lock on 'app/web'" in err
    assert "extended freeze" in err
    assert "2026-12-31T00:00:00Z" in err
    assert "Would call" not in err


def test_create_namespace_rejects_namespace_flag(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = MagicMock()
    ctx.namespace = None

    with pytest.raises(SystemExit) as exc:
        _execute_generated(
            ctx=ctx,
            op_ids=["create_namespace"],
            action="create",
            resource="namespace",
            address="my-ns",
            namespace="prod",
            output_fmt=None,
            field=None,
            version_flag=None,
            dry_run=True,
            yes=True,
            file_path=None,
            confirm_mode=None,
            namespace_explicit=True,
        )
    assert exc.value.code == USAGE_ERROR
    assert "not valid for this command" in capsys.readouterr().err


def test_create_namespace_ignores_context_namespace(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False
    ctx.namespace = "prod"

    _execute_generated(
        ctx=ctx,
        op_ids=["create_namespace"],
        action="create",
        resource="namespace",
        address="my-ns",
        namespace=None,
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
        namespace_explicit=False,
    )
    err = capsys.readouterr().err
    assert "Would create namespace 'my-ns'." in err
    assert "not valid for this command" not in err


def test_create_global_permission_rejects_namespace_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.namespace = None

    with pytest.raises(SystemExit) as exc:
        _execute_generated(
            ctx=ctx,
            op_ids=["create_global_permission"],
            action="create",
            resource="globalpermission",
            address="dev-read",
            namespace="prod",
            output_fmt=None,
            field=None,
            version_flag=None,
            dry_run=True,
            yes=True,
            file_path=None,
            confirm_mode=None,
            namespace_explicit=True,
        )
    assert exc.value.code == USAGE_ERROR
    assert "not valid for this command" in capsys.readouterr().err


def test_get_namespace_rejects_explicit_namespace_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.namespace = None

    with pytest.raises(SystemExit) as exc:
        _execute_generated(
            ctx=ctx,
            op_ids=["list_namespaces", "show_namespace"],
            action="get",
            resource="namespace",
            address=None,
            namespace="prod",
            output_fmt=None,
            field=None,
            version_flag=None,
            dry_run=True,
            yes=True,
            file_path=None,
            confirm_mode=None,
            namespace_explicit=True,
        )
    assert exc.value.code == USAGE_ERROR
    assert "not valid for this command" in capsys.readouterr().err


def test_get_global_permission_ignores_context_namespace(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = True
    ctx.yes = False
    ctx.namespace = "prod"

    _execute_generated(
        ctx=ctx,
        op_ids=["list_global_permissions", "get_global_permission"],
        action="get",
        resource="globalpermission",
        address="dev-read",
        namespace=None,
        output_fmt=None,
        field=None,
        version_flag=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
        namespace_explicit=False,
    )
    err = capsys.readouterr().err
    assert "Would get global permission rule 'dev-read'." in err
    assert "not valid for this command" not in err
