"""Output formatting utilities.

Diagnostics go to stderr; payload goes to stdout. This ensures
`ocmo resolve … | kubectl apply -f -` is safe.

Colour is enabled only when stdout is a TTY and NO_COLOR / --no-color is not set.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------

_OUTPUT_FORMATS = ("table", "wide", "json", "yaml", "name", "path", "raw")


def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("OCMO_NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _default_output_format() -> str:
    env = os.environ.get("OCMO_OUTPUT")
    if env:
        if env not in _OUTPUT_FORMATS and not env.startswith("jsonpath="):
            print(f"Warning: OCMO_OUTPUT={env!r} is not valid; ignored.", file=sys.stderr)
            return "table" if sys.stdout.isatty() else "yaml"
        return env
    return "table" if sys.stdout.isatty() else "yaml"


def format_datetime(value: Any) -> str:
    """Convert a datetime or ISO-8601 string to local time for CLI display.

    Human-oriented format: ``May 22, 22:14:13`` in the current year, otherwise
    ``May 22, 2025, 22:14:13``. Always uses the system local timezone.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            from dateutil.parser import isoparse  # deferred

            value = isoparse(value)
        except Exception:
            return str(value)
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            local_dt = value.astimezone(tz=None)
            now = datetime.datetime.now(tz=local_dt.tzinfo)
        else:
            local_dt = value
            now = datetime.datetime.now()
        time_part = local_dt.strftime("%H:%M:%S")
        month_day = f"{local_dt.strftime('%b')} {local_dt.day},"
        if local_dt.year == now.year:
            return f"{month_day} {time_part}"
        return f"{month_day} {local_dt.year}, {time_part}"
    return str(value)


# Keys stripped from CLI output when they carry internal DB surrogate keys.
# Public identifiers (audit event UUIDs, global-permission rule ids, …) are kept.


def _should_hide_output_key(key: str, value: Any) -> bool:
    if key.startswith("_"):
        return True
    if key == "namespace_id":
        return True
    if key == "id" and isinstance(value, int):
        return True
    return False


_ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")


def as_dict(obj: Any, *, fallback_vars: bool = True) -> dict[str, Any]:
    """Normalize SDK model / mapping to dict for CLI output."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        payload = obj.to_dict()
        return payload if isinstance(payload, dict) else {}
    if fallback_vars:
        try:
            data = vars(obj)
            return data if isinstance(data, dict) else {}
        except TypeError:
            pass
    return {}


def sanitize_for_output(obj: Any) -> Any:
    """Recursively convert an object to a JSON-serializable structure."""
    if isinstance(obj, datetime.datetime):
        return format_datetime(obj)
    if isinstance(obj, str | int | float | bool | type(None)):
        return obj
    if isinstance(obj, dict):
        return {k: sanitize_for_output(v) for k, v in obj.items() if not _should_hide_output_key(k, v)}
    if isinstance(obj, list | tuple):
        return [sanitize_for_output(v) for v in obj]
    if hasattr(obj, "to_dict"):
        return sanitize_for_output(obj.to_dict())
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return f"<{type(obj).__name__}>"


# ---------------------------------------------------------------------------
# YAML dumper with multiline literal blocks
# ---------------------------------------------------------------------------


def _make_yaml_dumper() -> type:
    import yaml  # deferred

    class _LiteralStr(str):
        pass

    def _literal_representer(dumper: yaml.Dumper, data: _LiteralStr) -> yaml.Node:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")

    def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.Node:
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    class _Dumper(yaml.SafeDumper):
        pass

    _Dumper.add_representer(str, _str_representer)  # type: ignore[arg-type]
    _Dumper.add_representer(_LiteralStr, _literal_representer)  # type: ignore[arg-type]
    return _Dumper


def yaml_dumps(data: Any) -> str:
    """Dump data to YAML with multiline strings as literal blocks (|)."""
    import yaml  # deferred

    dumper = _make_yaml_dumper()
    return yaml.dump(data, Dumper=dumper, default_flow_style=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# Core emit
# ---------------------------------------------------------------------------


def emit(data: Any, fmt: str | None = None, *, columns: list[str] | None = None) -> None:
    """Write data to stdout in the requested format."""
    from ._sdk_dispatch import unwrap_list_payload  # deferred

    fmt = fmt or _default_output_format()
    data = sanitize_for_output(data)

    if fmt == "json":
        print(json.dumps(data, default=str, indent=2))
    elif fmt == "yaml":
        if isinstance(data, dict | list):
            print(yaml_dumps(data), end="")
        else:
            print(data)
    elif fmt in ("table", "wide"):
        rows = unwrap_list_payload(data)
        if rows is not None:
            emit_table(rows, columns or _infer_table_columns(rows))
        else:
            _emit_table_data(data, columns=columns)
    elif fmt == "name":
        rows = unwrap_list_payload(data)
        _emit_identifiers(rows if rows is not None else data, "name")
    elif fmt == "path":
        rows = unwrap_list_payload(data)
        _emit_identifiers(rows if rows is not None else data, "path")
    elif fmt == "raw":
        if isinstance(data, bytes):
            sys.stdout.buffer.write(data)
        else:
            print(data, end="")
    elif fmt.startswith("jsonpath="):
        _emit_jsonpath(data, fmt[9:])
    else:
        print(data)


def _emit_table_data(data: Any, *, columns: list[str] | None = None) -> None:
    rows = _as_table_rows(data)
    if rows:
        emit_table(rows, columns or _infer_table_columns(rows))
    elif isinstance(data, dict | list):
        print(yaml_dumps(data), end="")
    else:
        print(data)


def _as_table_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _infer_table_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Columns that have at least one non-empty value across all rows."""
    order: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                order.append(key)
    active = [k for k in order if any(_cell_nonempty(row.get(k)) for row in rows)]
    return active or order


def _cell_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, list | dict):
        return bool(value)
    return True


def _emit_identifiers(data: Any, field: str) -> None:
    """Print one identifier per line (name or path only — no fallback)."""
    items = data if isinstance(data, list) else [data]
    for item in items:
        if isinstance(item, dict):
            value = item.get(field)
            if value is not None and value != "":
                print(value)
        else:
            value = getattr(item, field, None)
            if value is not None and value != "":
                print(value)


def _emit_jsonpath(data: Any, expr: str) -> None:
    """Extract a dot-path from data; for lists, apply to every item."""
    from ._sdk_dispatch import unwrap_list_payload  # deferred

    parts = _parse_path(expr)
    rows = unwrap_list_payload(data)
    if rows is not None:
        for item in rows:
            _print_jsonpath_value(_resolve_path(item, parts))
        return
    if isinstance(data, list):
        for item in data:
            _print_jsonpath_value(_resolve_path(item, parts))
    else:
        _print_jsonpath_value(_resolve_path(data, parts))


def _parse_path(expr: str) -> list[str]:
    return [p for p in re.split(r"[.\[\]]", expr.lstrip("$.")) if p]


def _resolve_path(data: Any, parts: list[str]) -> Any:
    if not parts:
        return data
    part = parts[0]
    rest = parts[1:]

    if part == "*":
        if not isinstance(data, list):
            return None
        return [_resolve_path(item, rest) for item in data]

    if isinstance(data, dict):
        return _resolve_path(data.get(part), rest)

    if isinstance(data, list):
        if part.isdigit():
            try:
                return _resolve_path(data[int(part)], rest)
            except IndexError:
                return None
        return [_resolve_path(item, parts) for item in data]

    return None


def _print_jsonpath_value(value: Any) -> None:
    if value is None:
        return
    if isinstance(value, list):
        for item in value:
            _print_jsonpath_value(item)
        return
    if isinstance(value, dict | list):
        print(json.dumps(value, default=str, indent=2))
    else:
        print(value)


def extract_field(data: Any, field: str) -> None:
    """Extract a dot-path field; for lists, print one value per item."""
    from ._sdk_dispatch import unwrap_list_payload  # deferred

    parts = _parse_path(field)
    rows = unwrap_list_payload(data)
    target = rows if rows is not None else (data if isinstance(data, list) else [data])
    if not isinstance(target, list):
        target = [target]
    for item in target:
        _print_jsonpath_value(_resolve_path(item, parts))


# ---------------------------------------------------------------------------
# Table rendering (kubectl-style: borderless, aligned columns)
# ---------------------------------------------------------------------------


def emit_table(
    rows: list[dict[str, Any]],
    columns: list[str] | None = None,
) -> None:
    """Render a borderless kubectl-style table."""
    if not rows:
        return

    cols = columns or _infer_table_columns(rows)

    if sys.stdout.isatty() and _color_enabled():
        _emit_rich_table(rows, cols)
    else:
        _emit_plain_table(rows, cols)


def _emit_rich_table(rows: list[dict[str, Any]], cols: list[str]) -> None:
    from rich.console import Console
    from rich.table import Table

    table = Table(
        box=None,
        show_header=True,
        header_style="bold",
        show_edge=False,
        pad_edge=False,
        padding=(0, 2),
    )
    for col in cols:
        table.add_column(col.upper())
    for row in rows:
        table.add_row(*[_fmt_cell(row.get(c, "")) for c in cols])
    Console().print(table)


def _emit_plain_table(rows: list[dict[str, Any]], cols: list[str]) -> None:
    widths = {c: len(c) for c in cols}
    str_rows: list[dict[str, str]] = []
    for row in rows:
        sr = {c: _fmt_cell(row.get(c, "")) for c in cols}
        str_rows.append(sr)
        for c in cols:
            widths[c] = max(widths[c], len(sr[c]))

    header = "  ".join(c.upper().ljust(widths[c]) for c in cols)
    print(header)
    for sr in str_rows:
        print("  ".join(sr[c].ljust(widths[c]) for c in cols))


def _fmt_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return format_datetime(value)
    if isinstance(value, str) and _ISO_DATETIME_RE.match(value):
        return format_datetime(value)
    if isinstance(value, list):
        if not value:
            return ""
        if all(isinstance(item, str) for item in value):
            return ", ".join(value)
    if isinstance(value, dict | list):
        return yaml_dumps(value).rstrip("\n")
    return str(value)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def err(msg: str) -> None:
    print(msg, file=sys.stderr)


def status(msg: str) -> None:
    """Print a human-readable status line to stderr."""
    print(msg, file=sys.stderr)


def warn(msg: str) -> None:
    print(f"Warning: {msg}", file=sys.stderr)


def confirm(msg: str, *, yes: bool, default: bool = False) -> bool:
    if yes:
        return True
    if not sys.stdin.isatty():
        err(f"Non-interactive mode: use --yes to confirm '{msg}'")
        return False
    answer = input(f"{msg} [y/N] ").strip().lower()
    return answer in ("y", "yes")
