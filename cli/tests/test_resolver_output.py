"""Tests for resolver token output on create."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ocmo_cli._resolver_output import print_resolver_token, resolver_token_from_result
from ocmo_cli.commands.apply import _upload
from ocmo_cli.commands.generated import _execute_generated, _structured_output_includes_token


def test_resolver_token_from_result_token1() -> None:
    result = SimpleNamespace(to_dict=lambda: {"token1": "ocmort-abc123"})
    assert resolver_token_from_result(result) == "ocmort-abc123"


def test_resolver_token_from_result_rotate_token() -> None:
    result = {"token": "ocmort-rotated", "token_number": 1}
    assert resolver_token_from_result(result) == "ocmort-rotated"


def test_resolver_token_from_result_ignores_masked() -> None:
    result = {"token1": "ocmo***1234"}
    assert resolver_token_from_result(result) is None


def test_print_resolver_token(capsys: pytest.CaptureFixture[str]) -> None:
    assert print_resolver_token({"token1": "ocmort-create"}) is True
    assert capsys.readouterr().out == "ocmort-create\n"


def test_upload_prints_resolver_token_on_create(capsys: pytest.CaptureFixture[str]) -> None:
    view = MagicMock()
    view.update_resolver.side_effect = RuntimeError("not found")
    view.create_resolver.return_value = SimpleNamespace(
        to_dict=lambda: {"token1": "ocmort-from-create"},
    )

    created, result = _upload(view, "app/resolvers/svc", "{}", "resolver")
    assert created is True
    print_resolver_token(result)
    assert capsys.readouterr().out == "ocmort-from-create\n"


def test_structured_output_includes_token() -> None:
    assert _structured_output_includes_token("yaml", None) is True
    assert _structured_output_includes_token("name", None) is False
    assert _structured_output_includes_token("json", "token1") is True


def test_execute_generated_create_resolver_prints_token_for_name_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.create_resolver.return_value = SimpleNamespace(
        name="svc",
        path="app/resolvers/svc",
        node_type="resolver",
        author="alice",
        description="",
        configuration="{}",
        to_dict=lambda: {
            "name": "svc",
            "path": "app/resolvers/svc",
            "node_type": "resolver",
            "token1": "ocmort-cli",
        },
    )

    _execute_generated(
        ctx=ctx,
        op_ids=["create_resolver"],
        action="create",
        resource="resolver",
        address="app/resolvers/svc",
        namespace="prod",
        output_fmt="name",
        field=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )

    captured = capsys.readouterr()
    assert "app/resolvers/svc\n" in captured.out
    assert "ocmort-cli\n" in captured.out
    assert "Created resolver 'app/resolvers/svc'." in captured.err


def test_execute_generated_rotate_token_prints_only_token(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = True
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.rotate_resolver_token.return_value = SimpleNamespace(
        to_dict=lambda: {"token": "ocmort-rotated", "token_number": 1},
    )

    _execute_generated(
        ctx=ctx,
        op_ids=["rotate_resolver_token"],
        action="rotate",
        resource="token",
        address="app/resolvers/svc",
        namespace="prod",
        output_fmt=None,
        field=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode="destructive",
        sdk_extra={"token_number": 1},
    )

    captured = capsys.readouterr()
    assert captured.out == "ocmort-rotated\n"
    assert captured.err == ""
    view.rotate_resolver_token.assert_called_once()


def test_execute_generated_create_dry_run_status_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False

    _execute_generated(
        ctx=ctx,
        op_ids=["create_config"],
        action="create",
        resource="config",
        address="app/web",
        namespace="prod",
        output_fmt=None,
        field=None,
        dry_run=True,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )

    captured = capsys.readouterr()
    assert "Would create config 'app/web'" in captured.err
    assert "Would call" not in captured.err
    assert captured.out == ""


def test_execute_generated_update_config_emits_raw_document_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.no_color = True
    ctx.dry_run = False
    ctx.yes = False
    ctx.require_namespace.return_value = "prod"
    view = MagicMock()
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    view.update_config.return_value = SimpleNamespace(
        name="web",
        path="app/web",
        node_type="config",
        author="alice",
        description="",
        tags=SimpleNamespace(to_dict=lambda: {}),
        version_data=SimpleNamespace(
            version=2,
            tags=[],
            data="replicas: 5\n",
            updater="bob",
            updated_at="2026-01-02T00:00:00+00:00",
            deleted_at=None,
            to_dict=lambda: {
                "version": 2,
                "tags": [],
                "data": "replicas: 5\n",
                "updater": "bob",
                "updated_at": "2026-01-02T00:00:00+00:00",
                "deleted_at": None,
            },
        ),
        to_dict=lambda: {
            "name": "web",
            "path": "app/web",
            "node_type": "config",
        },
    )

    _execute_generated(
        ctx=ctx,
        op_ids=["update_config"],
        action="update",
        resource="config",
        address="app/web",
        namespace="prod",
        output_fmt=None,
        field=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode=None,
    )

    captured = capsys.readouterr()
    assert captured.out == "replicas: 5\n"
    assert "# path: app/web" in captured.err
    assert "Updated config 'app/web'." in captured.err


def test_apply_cmd_prints_resolver_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    view = MagicMock()
    view.update_resolver.side_effect = RuntimeError("missing")
    view.create_resolver.return_value = SimpleNamespace(
        to_dict=lambda: {"token1": "ocmort-apply"},
    )
    ns = MagicMock()
    ns.update_resolver = view.update_resolver
    ns.create_resolver = view.create_resolver

    ctx = MagicMock()
    ctx.namespace = "prod"
    ctx.dry_run = False
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = ns
    ctx.namespace_view.return_value = ns
    from ocmo_cli.commands.apply import apply_cmd

    runner = CliRunner(mix_stderr=False)
    with patch("ocmo_cli.commands.apply.status") as status_mock:
        with runner.isolated_filesystem():
            with open("resolver.yaml", "w") as f:
                f.write("{}")
            result = runner.invoke(
                apply_cmd,
                ["app/resolvers/svc", "-f", "resolver.yaml", "-t", "resolver", "-n", "prod"],
                obj=ctx,
            )
    assert result.exit_code == 0, result.output
    assert result.stdout == "ocmort-apply\n"
    status_mock.assert_called_once_with("Created resolver 'app/resolvers/svc'.")
