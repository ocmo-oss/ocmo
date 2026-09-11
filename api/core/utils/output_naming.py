"""Resolved artifact naming: templates, placeholders, and deduplication."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ..shortcuts import SelectorLookupError, eval_selector, validate_selector_syntax

NAME_PLACEHOLDER_RE = re.compile(r"\{(\.[^{}]+)\}")
_OCMO_METADATA_PREFIX = "._ocmo."
_MAX_NAME_PATH_SEGMENTS = 5


class OutputNameError(Exception):
    """Raised when ``_ocmo.name`` template resolution fails."""


class _NamedOutput(Protocol):
    name: str


@dataclass(frozen=True, slots=True)
class NameOwnerContext:
    """Config that owns an ``_ocmo.name`` template."""

    path: str
    name: str
    version_tag: str
    version_number: int

    @property
    def path_segments(self) -> list[str]:
        return self.path.strip("/").split("/") if self.path else []


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

def validate_name_template_syntax(template: str) -> None:
    """Validate placeholder syntax in an ``_ocmo.name`` template (save-time)."""

    for expr in NAME_PLACEHOLDER_RE.findall(template):
        if expr.startswith(_OCMO_METADATA_PREFIX):
            meta_selector = "." + expr[len(_OCMO_METADATA_PREFIX) :]
            validate_selector_syntax(meta_selector)
        else:
            validate_selector_syntax(expr)


def validate_resolved_name(name: str) -> None:
    """Validate a fully resolved output name."""

    if name.startswith("/") or name.endswith("/"):
        raise OutputNameError("_ocmo.name resolved to a path that starts or ends with '/'")
    segments = name.split("/")
    if any(seg in (".", "..") for seg in segments):
        raise OutputNameError("_ocmo.name resolved to a path containing '.' or '..' segments")
    if len(segments) > _MAX_NAME_PATH_SEGMENTS:
        raise OutputNameError(
            f"_ocmo.name resolved to more than {_MAX_NAME_PATH_SEGMENTS} path segments"
        )
    if any(ord(ch) < 32 for ch in name):
        raise OutputNameError("_ocmo.name resolved to a value containing control characters")


def eval_config_metadata_selector(selector: str, owner: NameOwnerContext) -> Any:
    """Evaluate ``.Name``, ``.Path``, ``.Path[n]``, or ``.Version.*`` against *owner*."""

    if not selector or not selector.startswith("."):
        raise OutputNameError(f"Invalid metadata selector {selector!r}")
    if selector == ".Name":
        return owner.name
    if selector == ".Path":
        return owner.path
    m = re.match(r"^\.Path\[(-?\d+)\]$", selector)
    if m:
        segments = owner.path_segments
        idx = int(m.group(1))
        try:
            return segments[idx]
        except IndexError:
            raise OutputNameError(
                f"Path index {idx} out of range for {owner.path!r}"
            ) from None
    if selector == ".Version.tag":
        return owner.version_tag
    if selector == ".Version.number":
        return owner.version_number
    raise OutputNameError(f"Unsupported metadata selector {selector!r}")


def _coerce_placeholder_value(value: Any) -> str:
    if value is None:
        raise OutputNameError("placeholder resolved to null")
    if isinstance(value, (dict, list)):
        raise OutputNameError("placeholder resolved to non-scalar value")
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if "\n" in value or "\r" in value or "\0" in value:
            raise OutputNameError("placeholder resolved to a value containing control characters")
        return value
    return str(value)


def _placeholder_error(owner_path: str, placeholder: str, detail: str) -> OutputNameError:
    return OutputNameError(f"_ocmo.name on {owner_path}: placeholder {placeholder} {detail}")


def resolve_name_template(
    template: str,
    merged_data: Any,
    owner: NameOwnerContext,
) -> str:
    """Resolve ``{.selector}`` placeholders in *template* against merged data and metadata."""

    def _replace(match: re.Match[str]) -> str:
        expr = match.group(1)
        placeholder = "{" + expr + "}"
        try:
            validate_selector_syntax(expr)
        except ValueError as exc:
            raise _placeholder_error(owner.path, placeholder, f"has invalid syntax: {exc}") from exc

        try:
            if expr.startswith(_OCMO_METADATA_PREFIX):
                meta_selector = "." + expr[len(_OCMO_METADATA_PREFIX) :]
                raw = eval_config_metadata_selector(meta_selector, owner)
            else:
                raw = eval_selector(merged_data, expr)
        except SelectorLookupError:
            raise _placeholder_error(owner.path, placeholder, "not found in resolved data.") from None
        except OutputNameError as exc:
            if str(exc).startswith("_ocmo.name on "):
                raise
            raise _placeholder_error(owner.path, placeholder, str(exc)) from exc

        try:
            return _coerce_placeholder_value(raw)
        except OutputNameError as exc:
            raise _placeholder_error(owner.path, placeholder, str(exc).split(": ", 1)[-1]) from exc

    resolved = NAME_PLACEHOLDER_RE.sub(_replace, template)
    validate_resolved_name(resolved)
    return resolved


def finalize_output_name(
    *,
    name_template: str | None,
    merged_data: Any,
    owner: NameOwnerContext | None,
) -> str:
    """Compute the final artifact name for one output."""

    if owner is None:
        return "output"
    if name_template is None:
        return owner.name
    return resolve_name_template(name_template, merged_data, owner)
