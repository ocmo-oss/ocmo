"""Parse ``ocmo diff`` addresses and render unified diff output."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any

from ocmo._generated.types import UNSET

from ._address import AddressError, _validate_path, parse_address


@dataclass(frozen=True)
class DiffSpec:
    path: str
    from_ref: str | None = None
    to_ref: str | None = None
    to_path: str | None = None


def diff_sdk_kwargs(spec: DiffSpec, *, reveal: bool = False) -> tuple[str, dict[str, Any]]:
    """Return ``(path, kwargs)`` for ``NamespaceView.diff_item``."""
    kwargs: dict[str, Any] = {}
    if spec.from_ref is not None:
        kwargs["from_"] = spec.from_ref
    if spec.to_ref is not None:
        kwargs["to"] = spec.to_ref
    if spec.to_path is not None:
        kwargs["to_path"] = spec.to_path
    if reveal:
        kwargs["reveal"] = True
    return spec.path, kwargs


def parse_diff_spec(
    addresses: tuple[str, ...],
    *,
    version_flag: str | None = None,
    from_version: str | None = None,
    to_version: str | None = None,
) -> DiffSpec:
    """Resolve diff operands from positional addresses and version flags."""
    if not addresses:
        raise AddressError("At least one address is required.")
    if len(addresses) > 2:
        raise AddressError("Expected one or two addresses.")

    if len(addresses) == 2:
        if version_flag:
            raise AddressError(
                "Cannot use --version with two addresses; " "use @suffix or --from-version / --to-version."
            )
        if ".." in addresses[0] or ".." in addresses[1]:
            raise AddressError("Version range (..) is only supported with a single address.")
        from_path, from_ref = parse_address(addresses[0])
        to_path, to_ref = parse_address(addresses[1])
        return DiffSpec(
            path=from_path,
            from_ref=from_version or from_ref,
            to_ref=to_version or to_ref,
            to_path=to_path if to_path != from_path else None,
        )

    raw = addresses[0]
    if "@" in raw:
        path, version_part = raw.split("@", 1)
        if ".." in version_part:
            if version_flag:
                raise AddressError(
                    f"Conflicting version specifications: address suffix '@{version_part}' "
                    f"and --version '{version_flag}'. Provide only one."
                )
            _validate_path(path)
            range_from, range_to = _parse_version_range(version_part)
            return DiffSpec(
                path=path,
                from_ref=from_version or range_from,
                to_ref=to_version or range_to,
            )

    path, version = parse_address(raw, version_flag=version_flag)
    return DiffSpec(
        path=path,
        from_ref=from_version,
        to_ref=to_version or version,
    )


def _parse_version_range(version_part: str) -> tuple[str, str]:
    left, sep, right = version_part.partition("..")
    if not sep or not left or not right:
        raise AddressError(f"Invalid version range '@{version_part}'; expected path@FROM..TO.")
    return left, right


def diff_side_label(side: Any) -> str:
    requested = getattr(side, "requested", None) or ""
    path = getattr(side, "path", "")
    if requested:
        return f"{path}@{requested}"
    version = getattr(side, "version", None)
    if version is not None:
        return f"{path}@v{version}"
    return path


def _side_text(side: Any) -> str:
    data = getattr(side, "data", UNSET)
    if data is UNSET or data is None:
        return ""
    return str(data)


def render_unified_diff(from_text: str, to_text: str, *, from_label: str, to_label: str) -> str:
    if from_text == to_text:
        return "No differences\n"
    lines = difflib.unified_diff(
        from_text.splitlines(keepends=True),
        to_text.splitlines(keepends=True),
        fromfile=from_label,
        tofile=to_label,
    )
    rendered = "".join(lines)
    return rendered or "No differences\n"


def render_diff_response(result: Any) -> str:
    """Build unified diff text from an SDK ``DiffResponseSchema``."""
    if getattr(result, "decryption_required", False):
        return ""

    from_text = _side_text(result.from_side)
    to_text = _side_text(result.to_side)

    if getattr(result, "identical", False) is True:
        return "No differences\n"

    return render_unified_diff(
        from_text,
        to_text,
        from_label=diff_side_label(result.from_side),
        to_label=diff_side_label(result.to_side),
    )
