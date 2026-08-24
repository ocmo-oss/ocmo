"""ASCII resolve-series chart output (simplified frontend ResolveStatsChart)."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Any, cast

from ._output import format_datetime
from ._resolve_series import bucket_values

CHART_HEIGHT = 18
Y_AXIS_WIDTH = 5

_SERIES_MARKERS = {
    "cyan": "●",
    "yellow": "◆",
    "red": "✕",
}
_COLLISION_MARKER = "⊕"
_COLLISION_STYLE = "bold white"


@dataclass(frozen=True)
class _Cell:
    char: str
    style: str = ""


def _chart_width() -> int:
    try:
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    except OSError:
        columns = 80
    return max(24, min(columns - Y_AXIS_WIDTH - 2, 96))


def _resample(values: list[int], width: int) -> list[int]:
    if width <= 0:
        return []
    if not values:
        return [0] * width
    if len(values) <= width:
        return list(values)
    result: list[int] = []
    for index in range(width):
        start = index * len(values) // width
        end = (index + 1) * len(values) // width
        chunk = values[start:end] or [0]
        result.append(max(chunk))
    return result


def _bucket_x(index: int, count: int, width: int) -> int:
    """Map bucket index to plot column (spread across full chart width)."""
    if count <= 1:
        return width // 2
    return int(round(index * (width - 1) / (count - 1)))


def _series_plot_points(values: list[int], width: int) -> list[tuple[int, int]]:
    """Return (x, value) pairs covering the full plot width."""
    if not values or width <= 0:
        return []
    if len(values) > width:
        sampled = _resample(values, width)
        return [(index, value) for index, value in enumerate(sampled)]
    return [(_bucket_x(index, len(values), width), value) for index, value in enumerate(values)]


def _value_to_row(value: int, *, peak: int, height: int) -> int:
    if peak <= 0 or value <= 0:
        return height - 1
    ratio = value / peak
    return height - 1 - int(round(ratio * (height - 1)))


def _draw_line(
    grid: list[list[_Cell]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    *,
    style: str,
) -> None:
    width = len(grid[0])
    height = len(grid)
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        if 0 <= x < width and 0 <= y < height:
            current = grid[y][x]
            if current.char in (" ", "·"):
                grid[y][x] = _Cell("·", style)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _place_marker(
    grid: list[list[_Cell]],
    x: int,
    y: int,
    *,
    style: str,
    marker: str,
) -> None:
    height = len(grid)
    width = len(grid[0])
    if not (0 <= x < width and 0 <= y < height):
        return
    current = grid[y][x]
    if current.char in (" ", "·"):
        grid[y][x] = _Cell(marker, style)
        return
    if current.char == marker and current.style == style:
        return
    grid[y][x] = _Cell(_COLLISION_MARKER, _COLLISION_STYLE)


def _plot_series(
    grid: list[list[_Cell]],
    values: list[int],
    *,
    width: int,
    height: int,
    peak: int,
    style: str,
    marker: str,
) -> None:
    plot_points = _series_plot_points(values, width)
    points = [(x, _value_to_row(value, peak=peak, height=height)) for x, value in plot_points]
    if not points:
        return
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        _draw_line(grid, x0, y0, x1, y1, style=style)
    for x, value in plot_points:
        if value <= 0:
            continue
        y = _value_to_row(value, peak=peak, height=height)
        _place_marker(grid, x, y, style=style, marker=marker)


def _empty_grid(width: int, height: int) -> list[list[_Cell]]:
    return [[_Cell(" ") for _ in range(width)] for _ in range(height)]


def _y_axis_labels(peak: int, height: int) -> list[str]:
    if peak <= 0:
        return ["0"] * height
    labels: list[str] = []
    for row in range(height):
        value = int(round(peak * (height - 1 - row) / max(height - 1, 1)))
        labels.append(str(value))
    return labels


def _build_chart_grid(
    direct: list[int],
    nested: list[int],
    errors: list[int],
    *,
    width: int,
    show_nested: bool,
) -> tuple[list[list[_Cell]], int]:
    peak = max(1, *direct, *nested, *errors)
    grid = _empty_grid(width, CHART_HEIGHT)
    _plot_series(
        grid,
        errors,
        width=width,
        height=CHART_HEIGHT,
        peak=peak,
        style="red",
        marker=_SERIES_MARKERS["red"],
    )
    if show_nested:
        _plot_series(
            grid,
            nested,
            width=width,
            height=CHART_HEIGHT,
            peak=peak,
            style="yellow",
            marker=_SERIES_MARKERS["yellow"],
        )
    _plot_series(
        grid,
        direct,
        width=width,
        height=CHART_HEIGHT,
        peak=peak,
        style="cyan",
        marker=_SERIES_MARKERS["cyan"],
    )
    return grid, peak


def _x_axis_tick_row(bucket_count: int, width: int) -> list[_Cell]:
    """One tick per bucket column; duplicate x positions share a single tick."""
    row = [_Cell("─", "dim") for _ in range(width)]
    if bucket_count <= 0:
        return row
    for index in range(bucket_count):
        x = _bucket_x(index, bucket_count, width)
        if 0 <= x < width:
            row[x] = _Cell("┴", "dim")
    return row


def _bucket_axis_labels(buckets: list[dict[str, Any]]) -> tuple[str, str]:
    if not buckets:
        return "", ""
    left = format_datetime(buckets[0].get("start"))
    right = format_datetime(buckets[-1].get("start"))
    return left, right


def _direct_label(node_type: str) -> str:
    return "Resolves" if node_type == "resolver" else "Direct"


def _use_color() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("OCMO_NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _format_bucket_rows(
    buckets: list[dict[str, Any]],
) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for bucket in buckets:
        rows.append(
            (
                format_datetime(bucket.get("start")),
                str(int(bucket.get("direct") or 0)),
                str(int(bucket.get("nested") or 0)),
                str(int(bucket.get("errors") or 0)),
            )
        )
    return rows


def _print_plain_bucket_table(
    rows: list[tuple[str, str, str, str]],
    *,
    show_nested: bool,
    direct_label: str,
) -> None:
    if show_nested:
        headers: tuple[str, ...] = ("When", direct_label, "Nested", "Errors")
        data_rows = cast(list[tuple[str, ...]], rows)
    else:
        headers = ("When", direct_label, "Errors")
        data_rows = [(when, direct, errors) for when, direct, _nested, errors in rows]

    widths = [len(header) for header in headers]
    for row in data_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def _line(cells: tuple[str, ...]) -> str:
        parts = [
            cells[0].ljust(widths[0]),
            *[cells[i].rjust(widths[i]) for i in range(1, len(cells))],
        ]
        return "  ".join(parts)

    print(_line(headers))
    print(_line(tuple("-" * width for width in widths)))
    for row in data_rows:
        print(_line(row))


def print_resolve_series_chart(
    data: dict[str, Any],
    *,
    node_type: str,
    range_start: Any,
    range_end: Any,
) -> None:
    """Print a coloured line chart and per-bucket value table to stdout."""
    buckets, direct, nested, errors = bucket_values(data)
    width = _chart_width()
    show_nested = node_type != "resolver"
    direct_label = _direct_label(node_type)

    totals = {
        "direct": sum(direct),
        "nested": sum(nested),
        "errors": sum(errors),
    }
    has_activity = any(value > 0 for series in (direct, nested, errors) for value in series)

    start_label = format_datetime(range_start)
    end_label = format_datetime(range_end)
    grid, peak = _build_chart_grid(
        direct,
        nested,
        errors,
        width=width,
        show_nested=show_nested,
    )
    y_labels = _y_axis_labels(peak, CHART_HEIGHT)
    tick_row = _x_axis_tick_row(len(buckets), width)
    axis_left, axis_right = _bucket_axis_labels(buckets)
    bucket_rows = _format_bucket_rows(buckets)

    if _use_color():
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text

        console = Console()
        header = Text()
        header.append("Resolves  ", style="bold")
        header.append(f"{start_label} – {end_label}")
        console.print(header)

        legend = Text("  ")
        legend.append("● ", style="bold cyan")
        legend.append(f"{direct_label} {totals['direct']}  ")
        if show_nested:
            legend.append("◆ ", style="bold yellow")
            legend.append(f"Nested {totals['nested']}  ")
        legend.append("✕ ", style="bold red")
        legend.append(f"Errors {totals['errors']}  ")
        legend.append("⊕ ", style="bold white")
        legend.append("overlap")
        console.print(legend)

        for row_index in range(CHART_HEIGHT):
            line = Text()
            line.append(f"{y_labels[row_index]:>{Y_AXIS_WIDTH}} ", style="dim")
            for cell in grid[row_index]:
                line.append(cell.char, style=cell.style or None)
            console.print(line)

        tick_line = Text()
        tick_line.append(" " * (Y_AXIS_WIDTH + 1))
        for cell in tick_row:
            tick_line.append(cell.char, style=cell.style or "dim")
        console.print(tick_line)

        axis = Text(" " * (Y_AXIS_WIDTH + 1))
        axis.append(axis_left, style="dim")
        if axis_right and axis_right != axis_left:
            axis.append(" " * max(1, width - len(axis_left) - len(axis_right)), style="dim")
            axis.append(axis_right, style="dim")
        console.print(axis)

        if buckets and not has_activity:
            console.print("No resolve activity in this range", style="dim")
        elif bucket_rows:
            table = Table(show_header=True, header_style="bold", pad_edge=False)
            table.add_column("When", style="dim", no_wrap=True)
            table.add_column(direct_label, justify="right", style="cyan")
            if show_nested:
                table.add_column("Nested", justify="right", style="yellow")
            table.add_column("Errors", justify="right", style="red")
            for when, d_val, n_val, e_val in bucket_rows:
                if show_nested:
                    table.add_row(when, d_val, n_val, e_val)
                else:
                    table.add_row(when, d_val, e_val)
            console.print()
            console.print(table)
        return

    print(f"Resolves  {start_label} – {end_label}")
    legend_parts = [f"{direct_label} {totals['direct']}"]
    if show_nested:
        legend_parts.append(f"Nested {totals['nested']}")
    legend_parts.append(f"Errors {totals['errors']}")
    print("  " + "  ".join(legend_parts) + "  ⊕ overlap")

    for row_index in range(CHART_HEIGHT):
        body = "".join(cell.char for cell in grid[row_index])
        print(f"{y_labels[row_index]:>{Y_AXIS_WIDTH}} {body}")
    print(f"{' ' * Y_AXIS_WIDTH} {''.join(cell.char for cell in tick_row)}")
    print(f"{' ' * (Y_AXIS_WIDTH + 1)}{axis_left}", end="")
    if axis_right and axis_right != axis_left:
        print(f"{' ' * max(1, width - len(axis_left) - len(axis_right))}{axis_right}")
    else:
        print()

    if buckets and not has_activity:
        print("No resolve activity in this range")
    elif bucket_rows:
        print()
        _print_plain_bucket_table(
            bucket_rows,
            show_nested=show_nested,
            direct_label=direct_label,
        )
