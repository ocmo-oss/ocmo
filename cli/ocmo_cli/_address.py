"""Address parsing for OCMO tree paths.

Grammar: <tree-path>[@<version>]
         version := latest | stable | <custom-tag> | <integer>

Each path segment must match [a-zA-Z0-9_.-]+.
"""

from __future__ import annotations

import re

_SEGMENT_RE = re.compile(r"^[a-zA-Z0-9_./-]+$")
_BAD_CHARS = re.compile(r"[^a-zA-Z0-9_./\-@]")

# Characters allowed in individual path segments (no slash, no @)
_SEG_CHARS_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


class AddressError(ValueError):
    pass


def parse_simple_address(raw: str, *, version_flag: str | None = None) -> tuple[str, str | None]:
    """Parse ADDRESS for non-tree resources (namespace name, rule id, …)."""
    if not raw:
        raise AddressError("Address must not be empty.")

    if "@" in raw:
        path, suffix_version = raw.split("@", 1)
        if not suffix_version:
            raise AddressError(f"Empty version after '@' in address {raw!r}.")
    else:
        path, suffix_version = raw, None

    if suffix_version and version_flag and suffix_version != version_flag:
        raise AddressError(
            f"Conflicting version specifications: address suffix '@{suffix_version}' "
            f"and --version '{version_flag}'. Provide only one."
        )
    version = suffix_version or version_flag

    if not path.strip():
        raise AddressError("Address must not be empty.")

    return path, version


def parse_address(raw: str, *, version_flag: str | None = None) -> tuple[str, str | None]:
    """Parse a raw address string into (path, version).

    Raises AddressError with an actionable message on invalid input.
    Raises AddressError when both a @suffix and --version flag specify
    different values.
    """
    if not raw:
        raise AddressError("Address must not be empty.")

    # Split on first @
    if "@" in raw:
        path, suffix_version = raw.split("@", 1)
        if not suffix_version:
            raise AddressError(f"Empty version after '@' in address {raw!r}.")
    else:
        path, suffix_version = raw, None

    # Validate --version / @suffix conflict
    if suffix_version and version_flag and suffix_version != version_flag:
        raise AddressError(
            f"Conflicting version specifications: address suffix '@{suffix_version}' "
            f"and --version '{version_flag}'. Provide only one."
        )
    version = suffix_version or version_flag

    # Validate path characters
    _validate_path(path)

    return path, version


def _validate_path(path: str) -> None:
    """Raise AddressError if path contains illegal characters."""
    if not path:
        raise AddressError("Path must not be empty.")
    # Normalise trailing slash (allowed, marks folder)
    check = path.rstrip("/")
    if not check:
        raise AddressError("Path must not be only slashes.")
    for segment in check.split("/"):
        if not segment:
            raise AddressError(f"Path {path!r} contains an empty segment (double slash).")
        m = _BAD_CHARS.search(segment)
        if m:
            raise AddressError(
                f"Path segment {segment!r} contains illegal character {m.group()!r}. "
                "Allowed: letters, digits, underscore, hyphen, dot."
            )
        if not _SEG_CHARS_RE.match(segment):
            raise AddressError(f"Path segment {segment!r} contains characters outside [a-zA-Z0-9_.-].")


def is_folder_address(raw: str) -> bool:
    """Return True when the path ends with '/' (marks a folder)."""
    path = raw.split("@")[0]
    return path.endswith("/")


def resolve_relocate_target(source_path: str, target_path: str) -> str:
    """Resolve TARGET for move/copy using Unix-style directory semantics.

    When ``target_path`` ends with ``/``, the source item is placed inside that
    directory under its current leaf name. Otherwise ``target_path`` is the exact
    destination path.
    """
    if not target_path.endswith("/"):
        return target_path

    parent = target_path.rstrip("/")
    name = source_path.rstrip("/").split("/")[-1]
    if parent:
        return f"{parent}/{name}"
    return name


def slug(name: str) -> str:
    """Produce a tree-safe slug from an arbitrary filesystem name.

    NFC-normalise, replace runs of forbidden characters with '-',
    trim leading/trailing '-'. Case is preserved.
    """
    import unicodedata

    normalised = unicodedata.normalize("NFC", name)
    result = re.sub(r"[^A-Za-z0-9\-_.]", "-", normalised)
    result = re.sub(r"-{2,}", "-", result)
    result = result.strip("-")
    return result or "-"


def parse_address_or_exit(raw: str, *, version_flag: str | None = None) -> tuple[str, str | None]:
    """Parse a tree address or exit with USAGE_ERROR."""
    try:
        return parse_address(raw, version_flag=version_flag)
    except AddressError as exc:
        from ._exit import USAGE_ERROR
        from ._output import err

        err(str(exc))
        raise SystemExit(USAGE_ERROR) from exc


def parse_simple_address_or_exit(
    raw: str,
    *,
    version_flag: str | None = None,
) -> tuple[str, str | None]:
    """Parse a simple address or exit with USAGE_ERROR."""
    try:
        return parse_simple_address(raw, version_flag=version_flag)
    except AddressError as exc:
        from ._exit import USAGE_ERROR
        from ._output import err

        err(str(exc))
        raise SystemExit(USAGE_ERROR) from exc


def reject_version(
    version: str | None,
    *,
    command: str,
    allow_flag: bool = False,
) -> None:
    """Exit when ADDRESS includes @version (and optionally mention --version)."""
    if not version:
        return
    from ._exit import USAGE_ERROR
    from ._output import err

    suffix = " or --version" if allow_flag else ""
    err(f"{command} ADDRESS does not support @version{suffix}.")
    raise SystemExit(USAGE_ERROR)
