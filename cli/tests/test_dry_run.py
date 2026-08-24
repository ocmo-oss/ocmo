"""Tests for user-facing dry-run plan messages."""

from __future__ import annotations

from ocmo_cli._dry_run import (
    emit_dry_run_plan,
    format_apply_dry_run,
    format_generated_dry_run,
    format_resolve_dry_run,
)


def test_format_create_namespace_includes_description() -> None:
    lines = format_generated_dry_run(
        op_id="create_namespace",
        action="create",
        resource="namespace",
        path="my-ns",
        version=None,
        namespace=None,
        args=[],
        kwargs={"body": {"name": "my-ns", "description": "Prod workloads"}},
        client_scope=True,
    )
    assert lines == [
        "Would create namespace 'my-ns'. Description: 'Prod workloads'.",
    ]


def test_format_create_global_permission_includes_position_step() -> None:
    lines = format_generated_dry_run(
        op_id="create_global_permission",
        action="create",
        resource="globalpermission",
        path="dev-read",
        version=None,
        namespace=None,
        args=[],
        kwargs={"body": {"id": "dev-read", "namespace": "dev/*"}},
        client_scope=True,
        file_path="rule.yaml",
        gp_create_position=1.5,
    )
    assert lines == [
        "Would create global permission rule 'dev-read' from 'rule.yaml'.",
        "Would set rule position to 1.5.",
    ]


def test_format_delete_item_includes_namespace_and_version() -> None:
    lines = format_generated_dry_run(
        op_id="delete_item",
        action="delete",
        resource="item",
        path="app/web",
        version="stable",
        namespace="prod",
        args=["app/web"],
        kwargs={"version": "stable"},
        client_scope=False,
    )
    assert lines == [
        "Would delete version 'stable' of item 'app/web' in namespace 'prod' " "(not the item itself).",
    ]


def test_format_delete_item_without_version_deletes_whole_item() -> None:
    lines = format_generated_dry_run(
        op_id="delete_item",
        action="delete",
        resource="item",
        path="app/web",
        version=None,
        namespace="prod",
        args=["app/web"],
        kwargs={},
        client_scope=False,
    )
    assert lines == ["Would delete item 'app/web' in namespace 'prod'."]


def test_format_move_item_into_directory_includes_resolved_destination() -> None:
    lines = format_generated_dry_run(
        op_id="move_item",
        action="move",
        resource="item",
        path="b/c/d",
        version=None,
        namespace="my-first-namespace",
        args=[],
        kwargs={"target_path": "a/d"},
        client_scope=False,
    )
    assert lines == [
        "Would move item 'b/c/d' to 'a/d' in namespace 'my-first-namespace'.",
        "After move, item will be available at 'a/d'.",
    ]


def test_format_move_item_includes_destination_note() -> None:
    lines = format_generated_dry_run(
        op_id="move_item",
        action="move",
        resource="item",
        path="b/c/d",
        version=None,
        namespace="my-first-namespace",
        args=[],
        kwargs={"target_path": "a"},
        client_scope=False,
    )
    assert lines == [
        "Would move item 'b/c/d' to 'a' in namespace 'my-first-namespace'.",
        "After move, item will be available at 'a'.",
    ]


def test_format_tag_item() -> None:
    lines = format_generated_dry_run(
        op_id="set_tag",
        action="tag",
        resource="item",
        path="app/web",
        version=None,
        namespace="prod",
        args=["app/web"],
        kwargs={"tag": "release"},
        client_scope=False,
    )
    assert lines == ["Would tag item 'app/web' as 'release' in namespace 'prod'."]


def test_format_apply_dry_run() -> None:
    message = format_apply_dry_run(
        kind="config",
        path="app/web",
        source_name="app.json",
        namespace="prod",
    )
    assert message == ("Would create or update config 'app/web' from 'app.json' in namespace 'prod'.")


def test_format_resolve_dry_run() -> None:
    lines = format_resolve_dry_run(
        path="app/web",
        namespace="prod",
        cast="json",
        parameters={"replicas": 3},
    )
    assert lines[0] == "Would resolve 'app/web' in namespace 'prod'."
    assert "Cast output as json." in lines
    assert "Parameters: replicas=3." in lines


def test_emit_dry_run_plan_writes_to_stderr(capsys) -> None:
    emit_dry_run_plan("Would create config 'app/web' in namespace 'prod'.")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "[dry-run] Would create config 'app/web' in namespace 'prod'.\n"
