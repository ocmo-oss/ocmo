"""Helpers for ``ocmo get version`` address and query handling."""

from __future__ import annotations

from typing import Any


def resolve_tag_version_number(
    view: Any,
    path: str,
    version_ref: str | None,
) -> int:
    """Resolve a version reference to a concrete version number for ``set_tag``.

    When *version_ref* is omitted or ``latest``, the highest version number is
    returned. Numeric refs are returned as-is; tag names (``stable``, custom tags)
    are looked up via ``list_item_versions``.
    """
    from ._exit import NOT_FOUND
    from ._output import as_dict, err

    if version_ref and version_ref.isdigit():
        return int(version_ref)

    list_kwargs: dict[str, Any] = {"limit": 1}
    if version_ref and version_ref != "latest":
        list_kwargs["q"] = version_ref

    result = view.list_item_versions(path=path, **list_kwargs)
    data = as_dict(result) or {}
    versions = data.get("versions")
    if not isinstance(versions, list) or not versions:
        if version_ref:
            err(f"Version or tag {version_ref!r} not found for item {path!r}.")
        else:
            err(f"Item {path!r} has no versions.")
        raise SystemExit(NOT_FOUND)

    first = versions[0]
    version_number = first.get("version") if isinstance(first, dict) else getattr(first, "version", None)
    if version_number is None:
        err(f"Could not determine version number for item {path!r}.")
        raise SystemExit(NOT_FOUND)
    return int(version_number)


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
