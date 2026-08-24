"""Resolve command output formatting."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from ._output import (
    _parse_path,
    _print_jsonpath_value,
    _resolve_path,
    sanitize_for_output,
    yaml_dumps,
)
from ._typing import ResolvedArtifact

_METADATA_FIELDS = ("name", "version", "format", "checksum")
_TRACE_BASE_INDENT = 2


def resolve_output_format(
    cli_fmt: str | None,
    ctx_fmt: str | None,
    *,
    command_key: str = "resolve",
) -> str:
    """Pick the effective resolve/document output format."""
    from ._output_manifest import get_command_spec, resolve_effective_format

    return resolve_effective_format(cli_fmt, ctx_fmt, get_command_spec(command_key))


def _stderr_color_enabled(*, no_color: bool = False) -> bool:
    if no_color or os.environ.get("NO_COLOR") or os.environ.get("OCMO_NO_COLOR"):
        return False
    return sys.stderr.isatty()


def _item_metadata(item: ResolvedArtifact) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for key in _METADATA_FIELDS:
        value = getattr(item, key, None)
        if value is not None and value != "":
            rows.append((key, value))
    return rows


def _trace_metadata_lines(item: ResolvedArtifact) -> list[str]:
    trace = sanitize_for_output(getattr(item, "trace", {}) or {})
    if not trace:
        return []
    yaml_text = yaml_dumps(trace).rstrip("\n")
    if not yaml_text or yaml_text == "{}":
        return []
    lines = ["# trace:"]
    for line in yaml_text.splitlines():
        if not line.strip():
            continue
        yaml_indent = len(line) - len(line.lstrip(" "))
        content = line.lstrip(" ")
        prefix = "# " + (" " * (_TRACE_BASE_INDENT + yaml_indent))
        lines.append(f"{prefix}{content}")
    return lines


def _item_content(item: ResolvedArtifact) -> str:
    """Resolved artifact bytes as text for json/yaml output."""
    return item.text


def _item_payload(item: ResolvedArtifact, *, include_data: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": getattr(item, "name", None),
        "version": getattr(item, "version", None),
        "format": getattr(item, "format", None),
        "checksum": getattr(item, "checksum", None),
        "trace": sanitize_for_output(getattr(item, "trace", {}) or {}),
    }
    if include_data:
        payload["data"] = _item_content(item)
    else:
        payload["url"] = getattr(item, "url", None)
    return payload


def _write_report_payload(outcomes: list[Any]) -> dict[str, Any]:
    from ._resolve_write import ResolveWriteOutcome

    items: list[dict[str, Any]] = []
    for outcome in outcomes:
        if not isinstance(outcome, ResolveWriteOutcome):
            continue
        item = outcome.item
        entry: dict[str, Any] = {
            "name": getattr(item, "name", None),
            "version": getattr(item, "version", None),
            "format": getattr(item, "format", None),
            "checksum": getattr(item, "checksum", None),
            "trace": sanitize_for_output(getattr(item, "trace", {}) or {}),
            "path": str(outcome.path),
            "result": outcome.result,
        }
        if outcome.detail:
            entry["detail"] = outcome.detail
        items.append(entry)
    return {"items": items, "length": len(items)}


def emit_write_outcome_jsonpath(outcome: Any, expr: str) -> None:
    """Print one filesystem write outcome field selected by jsonpath."""
    payload = _write_report_payload([outcome])
    value = _resolve_path(payload, _parse_path(expr))
    _print_jsonpath_value(value)


def emit_write_outcome(
    outcome: Any,
    fmt: str,
    *,
    no_color: bool = False,
) -> None:
    """Report one filesystem write outcome."""
    emit_write_report([outcome], fmt, no_color=no_color)


def emit_write_report(
    outcomes: list[Any],
    fmt: str,
    *,
    no_color: bool = False,
) -> None:
    """Report filesystem write outcomes to stderr (raw) or stdout (json/yaml)."""
    from ._resolve_write import ResolveWriteOutcome

    if fmt in ("json", "yaml"):
        payload = _write_report_payload(outcomes)
        if fmt == "json":
            print(json.dumps(payload, default=str, indent=2))
        else:
            print(yaml_dumps(payload), end="")
        return

    for outcome in outcomes:
        if not isinstance(outcome, ResolveWriteOutcome):
            continue
        path = outcome.path
        if outcome.result == "created":
            _err_meta(f"created {path}", no_color=no_color)
        elif outcome.result == "rewritten":
            _err_meta(f"rewritten {path}", no_color=no_color)
        elif outcome.result == "skipped":
            reason = outcome.detail or "unchanged"
            _err_meta(f"skipped {path} ({reason})", no_color=no_color)
        elif outcome.result == "failed":
            reason = outcome.detail or "failed"
            _err_meta(f"failed {path}: {reason}", no_color=no_color)


def _response_payload(items: list[Any], *, include_data: bool) -> dict[str, Any]:
    return {
        "items": [_item_payload(item, include_data=include_data) for item in items],
        "length": len(items),
    }


def _err_meta(line: str, *, no_color: bool = False) -> None:
    if _stderr_color_enabled(no_color=no_color):
        from rich.console import Console

        Console(stderr=True, highlight=False).print(line, style="bright_black")
    else:
        print(line, file=sys.stderr)


def emit_resolve_item_metadata(item: ResolvedArtifact, *, no_color: bool = False) -> None:
    """Write one item's resolve metadata to stderr as ``# key: value`` lines."""
    for key, value in _item_metadata(item):
        _err_meta(f"# {key}: {value}", no_color=no_color)
    for line in _trace_metadata_lines(item):
        _err_meta(line, no_color=no_color)


def emit_resolve_raw(items: list[ResolvedArtifact], *, no_color: bool = False) -> None:
    """Metadata on stderr, artifact content on stdout, blank line between items."""
    for index, item in enumerate(items):
        if index > 0:
            print()
        emit_resolve_item_metadata(item, no_color=no_color)
        text = item.text
        print(text, end="" if text.endswith("\n") else "\n")


def emit_resolve_results(
    items: list[ResolvedArtifact],
    fmt: str,
    *,
    no_color: bool = False,
    include_data: bool = True,
) -> None:
    """Emit resolved items in the requested resolve output format."""
    if fmt == "raw":
        if not include_data:
            for item in items:
                emit_resolve_item_metadata(item, no_color=no_color)
            return
        emit_resolve_raw(items, no_color=no_color)
        return

    if fmt == "name":
        for item in items:
            name = getattr(item, "name", None)
            if name:
                print(name)
        return

    payload = _response_payload(items, include_data=include_data)

    if fmt == "json":
        print(json.dumps(payload, default=str, indent=2))
    elif fmt == "yaml":
        print(yaml_dumps(payload), end="")
    elif fmt.startswith("jsonpath="):
        value = _resolve_path(payload, _parse_path(fmt[9:]))
        _print_jsonpath_value(value)
    else:
        print(payload)
