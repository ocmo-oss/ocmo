"""List/show helpers for ``ocmo get cast``."""

from __future__ import annotations

from typing import Any

GET_CAST_LIST_OUTPUT_KEY = "get cast list"


class CastFormatNotFoundError(ValueError):
    """Raised when a requested cast format name is not available."""


def is_get_cast_list_mode(*, action: str, resource: str, address: str | None) -> bool:
    return action == "get" and resource == "cast" and not address


def is_get_cast_show_mode(*, action: str, resource: str, address: str | None) -> bool:
    return action == "get" and resource == "cast" and bool(address)


def _formats_from_payload(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        formats = data.get("formats")
        if isinstance(formats, list):
            return [row for row in formats if isinstance(row, dict)]
    return []


def cast_list_rows(data: Any) -> list[dict[str, str]]:
    """Return one row per cast format name for list output."""
    rows: list[dict[str, str]] = []
    for entry in _formats_from_payload(data):
        name = entry.get("format")
        if isinstance(name, str) and name:
            rows.append({"format": name})
    return rows


def cast_show_payload(data: Any, format_name: str) -> dict[str, Any]:
    """Return one cast format entry (format + options_schema) for show output."""
    target = format_name.casefold()
    for entry in _formats_from_payload(data):
        name = entry.get("format")
        if isinstance(name, str) and name.casefold() == target:
            return {
                "format": name,
                "options_schema": entry.get("options_schema") or {},
            }
    raise CastFormatNotFoundError(f"Unknown cast format {format_name!r}.")
