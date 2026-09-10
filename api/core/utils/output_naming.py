"""Resolved artifact naming helpers (suffixes and deduplication)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class _NamedOutput(Protocol):
    name: str


def split_name_extension(name: str) -> tuple[str, str]:
    """Split *name* into stem and extension on the last ``.`` when present."""

    if "." in name and not name.startswith("."):
        stem, ext = name.rsplit(".", 1)
        if ext:
            return stem, f".{ext}"
    return name, ""


def apply_numeric_suffix(name: str, index: int) -> str:
    """Insert ``-{index}`` before the file extension."""

    stem, ext = split_name_extension(name)
    return f"{stem}-{index}{ext}"


def replicate_output_name(base_name: str, one_based_index: int) -> str:
    """Return *base_name* with a 1-based numeric suffix before the extension."""

    return apply_numeric_suffix(base_name, one_based_index)


def deduplicate_output_names(outputs: Sequence[_NamedOutput]) -> None:
    """Ensure unique ``name`` values when there are multiple outputs.

    The first occurrence keeps its name; later duplicates get ``-1``, ``-2``, …
    inserted before the extension.
    """

    if len(outputs) <= 1:
        return

    seen: dict[str, int] = {}
    for output in outputs:
        name = output.name
        if name not in seen:
            seen[name] = 0
            continue
        seen[name] += 1
        output.name = apply_numeric_suffix(name, seen[name])
