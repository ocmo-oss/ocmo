"""Helpers for ``ocmo get version`` address and query handling."""

from __future__ import annotations

from typing import Any


def apply_version_address_query(extra: dict[str, Any], version: str | None) -> None:
    """Map ADDRESS@VER suffix to list_item_versions query parameters.

    ``@latest``, ``@stable``, and other tag names are passed as ``q`` (search),
    not as implicit ``limit=1`` — a tag may point at an older version.
    """
    if not version or extra.get("q") is not None:
        return
    extra.setdefault("q", version)


def emit_item_versions_output(
    view: Any,
    path: str,
    *,
    version: str | None,
    output_fmt: str | None,
    ctx_fmt: str | None,
    field: str | None = None,
) -> None:
    """Emit version history for *path* using ``get version`` output formatting."""
    from ._output import as_dict, extract_field, sanitize_for_output
    from ._output_manifest import emit_command_output

    list_kwargs: dict[str, Any] = {}
    apply_version_address_query(list_kwargs, version)
    result = view.list_item_versions(path=path, **list_kwargs)
    data = as_dict(result)
    if field:
        extract_field(sanitize_for_output(data), field)
        return
    emit_command_output("get version", data, output_fmt, ctx_fmt=ctx_fmt)
