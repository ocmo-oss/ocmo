"""Tests for resolve-series chart rendering."""

from __future__ import annotations

import io
from contextlib import redirect_stdout

from ocmo_cli._resolve_series_chart import (
    CHART_HEIGHT,
    _build_chart_grid,
    _empty_grid,
    _place_marker,
    _series_plot_points,
    _x_axis_tick_row,
    print_resolve_series_chart,
)


def test_series_plot_points_spreads_buckets_across_width() -> None:
    points = _series_plot_points([1, 2, 3, 4, 5], width=40)
    assert points[0][0] == 0
    assert points[-1][0] == 39
    assert len(points) == 5


def test_series_plot_points_downsamples_when_many_buckets() -> None:
    values = list(range(100))
    points = _series_plot_points(values, width=20)
    assert len(points) == 20
    assert points[0][0] == 0
    assert points[-1][0] == 19


def test_x_axis_tick_row_marks_each_bucket() -> None:
    row = _x_axis_tick_row(5, width=40)
    tick_columns = [index for index, cell in enumerate(row) if cell.char == "┴"]
    assert tick_columns == [0, 10, 20, 29, 39]


def test_place_marker_collision_uses_overlap_glyph() -> None:
    grid = _empty_grid(10, 10)
    _place_marker(grid, 3, 4, style="cyan", marker="●")
    _place_marker(grid, 3, 4, style="red", marker="✕")
    assert grid[4][3].char == "⊕"


def test_build_chart_grid_uses_configured_height() -> None:
    grid, peak = _build_chart_grid([2, 5], [1, 0], [0, 1], width=12, show_nested=True)
    assert len(grid) == CHART_HEIGHT
    assert peak >= 5
    assert any(cell.char == "●" for row in grid for cell in row)


def test_print_resolve_series_chart_includes_bucket_value_table() -> None:
    buffer = io.StringIO()
    data = {
        "bucket_seconds": 86400,
        "buckets": [
            {"start": "2026-08-01T00:00:00+00:00", "direct": 2, "nested": 1, "errors": 0},
            {"start": "2026-08-02T00:00:00+00:00", "direct": 5, "nested": 0, "errors": 1},
        ],
    }
    with redirect_stdout(buffer):
        print_resolve_series_chart(
            data,
            node_type="config",
            range_start="2026-07-01T00:00:00+00:00",
            range_end="2026-08-02T00:00:00+00:00",
        )
    output = buffer.getvalue()
    assert "When" in output
    assert "Direct" in output
    assert "Nested" in output
    assert "Errors" in output
    assert "2" in output
    assert "5" in output
    assert output.count("\n") >= CHART_HEIGHT + 4
