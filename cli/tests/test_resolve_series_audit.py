"""Tests for hand-written ``ocmo resolve-series audit``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._resolve_series import (
    pick_resolve_bucket_seconds,
    resolve_bucket_seconds,
    resolve_time_range,
)
from ocmo_cli.commands.resolve_series import resolve_series_audit_cmd
from ocmo_cli.main import cli


def test_pick_resolve_bucket_seconds_matches_frontend_thresholds() -> None:
    assert pick_resolve_bucket_seconds(20 * 86400) == 86400
    assert pick_resolve_bucket_seconds(10 * 86400) == 12 * 3600
    assert pick_resolve_bucket_seconds(4 * 86400) == 4 * 3600
    assert pick_resolve_bucket_seconds(2 * 86400) == 2 * 3600
    assert pick_resolve_bucket_seconds(1 * 86400) == 3600
    assert pick_resolve_bucket_seconds(12 * 3600) == 3600
    assert pick_resolve_bucket_seconds(10 * 3600) == 1800


def test_resolve_time_range_defaults_to_last_30_days() -> None:
    end = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    start, resolved_end = resolve_time_range(None, end.isoformat())
    assert resolved_end == end
    assert resolved_end - start == timedelta(days=30)


def test_resolve_bucket_seconds_auto_from_range() -> None:
    start = datetime(2026, 7, 1, tzinfo=UTC)
    end = datetime(2026, 8, 1, tzinfo=UTC)
    assert resolve_bucket_seconds(start, end, override=None) == 86400


def test_resolve_series_audit_help_lists_expected_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve-series", "audit", "--help"])
    assert result.exit_code == 0, result.output
    assert "--from" in result.output
    assert "--to" in result.output
    assert "--bucket-seconds" in result.output
    assert "-o" in result.output or "--output" in result.output
    assert "chart" in result.output
    assert "--object-id" not in result.output
    assert "--object-type" not in result.output
    assert "--field" not in result.output
    assert "--file" not in result.output


def test_resolve_series_audit_rejects_invalid_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["-n", "prod", "resolve-series", "audit", "app/web", "-o", "table"],
    )
    assert result.exit_code != 0
    assert "not a valid output format" in result.output


def test_resolve_series_audit_calls_api_with_address_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_end = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "ocmo_cli.commands.resolve_series.resolve_time_range",
        lambda _from, _to: (
            fixed_end - timedelta(days=30),
            fixed_end,
        ),
    )

    view = MagicMock()
    view.get_item.return_value = MagicMock(node_type="config")
    view.namespace_audit_resolve_series.return_value = MagicMock(
        to_dict=lambda: {
            "bucket_seconds": 86400,
            "buckets": [
                {"start": "2026-08-01T00:00:00+00:00", "direct": 2, "nested": 1, "errors": 0},
                {"start": "2026-08-02T00:00:00+00:00", "direct": 5, "nested": 0, "errors": 1},
            ],
        },
    )

    ctx = MagicMock()
    ctx.output = None
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    runner = CliRunner()
    result = runner.invoke(
        resolve_series_audit_cmd,
        ["app/web", "-o", "yaml"],
        obj=ctx,
    )
    assert result.exit_code == 0, result.output
    view.namespace_audit_resolve_series.assert_called_once()
    call = view.namespace_audit_resolve_series.call_args
    assert call.kwargs["object_id"] == "app/web"
    assert call.kwargs["object_type"] == "config"
    assert call.kwargs["from_"] == fixed_end - timedelta(days=30)
    assert call.kwargs["to"] == fixed_end
    assert call.kwargs["bucket_seconds"] == 86400
    assert "bucket_seconds:" in result.output


def test_resolve_series_audit_chart_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_end = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "ocmo_cli.commands.resolve_series.resolve_time_range",
        lambda _from, _to: (
            fixed_end - timedelta(days=30),
            fixed_end,
        ),
    )

    view = MagicMock()
    view.get_item.return_value = MagicMock(node_type="config")
    view.namespace_audit_resolve_series.return_value = MagicMock(
        to_dict=lambda: {
            "bucket_seconds": 86400,
            "buckets": [
                {"start": "2026-08-01T00:00:00+00:00", "direct": 2, "nested": 1, "errors": 0},
                {"start": "2026-08-02T00:00:00+00:00", "direct": 5, "nested": 0, "errors": 1},
            ],
        },
    )

    ctx = MagicMock()
    ctx.output = None
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    runner = CliRunner()
    result = runner.invoke(
        resolve_series_audit_cmd,
        ["app/web", "-o", "chart"],
        obj=ctx,
    )
    assert result.exit_code == 0, result.output
    assert "Resolves" in result.output
    assert "Direct" in result.output
    assert "Nested" in result.output
    assert "Errors" in result.output
    assert "When" in result.output
    assert "    2" in result.output or "  2" in result.output
