"""Helpers for change-request body comparison and reference rewriting."""

from __future__ import annotations

import re

from ..shortcuts import is_change_request_ref, parse_ref

# Match @~N at end of a reference segment (after path)
_CR_REF_SUFFIX_RE = re.compile(r"@~([1-9][0-9]*)")


def normalize_for_substantive_compare(body: str) -> str:
    """Collapse CR ref suffixes to @~0 so CR→version-only edits compare equal."""

    return _CR_REF_SUFFIX_RE.sub("@~0", body)


def is_substantive_content_change(old_body: str, new_body: str) -> bool:
    """Return True when *new_body* is not only CR-ref→version ref rewrites vs *old_body*."""

    if old_body == new_body:
        return False
    if normalize_for_substantive_compare(old_body) == normalize_for_substantive_compare(new_body):
        return False
    return True


def rewrite_cr_ref_in_content(content: str, resource_path: str, cr_number: int, version: int) -> str:
    """Replace references to ``resource_path@~cr_number`` with ``resource_path@version``."""

    path = resource_path.strip("/")
    # References may be relative; match @~N when preceded by path ending
    pattern = re.compile(
        rf"((?:\.\./)*{re.escape(path)}|{re.escape(path)})@~{cr_number}\b",
    )
    return pattern.sub(lambda m: f"{m.group(1)}@{version}", content)


def collect_cr_refs_in_metadata_paths(
    refs: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Filter reference tuples whose version_ref is a change-request suffix."""
    out: list[tuple[str, str, str]] = []
    for node_type, path, version_ref in refs:
        if is_change_request_ref(version_ref):
            out.append((node_type, path, version_ref))
    return out


def ref_string_has_cr_suffix(ref: str) -> bool:
    if "@" not in ref:
        return False
    _, version = parse_ref(ref.rstrip("?"))
    return is_change_request_ref(version)
