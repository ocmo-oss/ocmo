"""Helpers for change-request body comparison and reference rewriting."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from ..shortcuts import (
    change_request_number_from_ref,
    is_change_request_ref,
    parse_ref,
    resolve_relative_path,
)

# Match @~N at end of a reference segment (after path)
_CR_REF_SUFFIX_RE = re.compile(r"@~([1-9][0-9]*)")
_REF_ANCHOR_LOOKBEHIND = r"(?<![\w./-])"


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


def change_request_cache_stamp(updated_at: datetime, content_plaintext: str) -> str:
    """Fingerprint change-request draft content for resolve-cache keys and revalidation."""
    digest = hashlib.sha256(content_plaintext.encode("utf-8")).hexdigest()[:16]
    ts = updated_at.timestamp() if updated_at else 0.0
    return f"{ts:.6f}:{digest}"


def _ref_span_used(start: int, end: int, used: list[tuple[int, int]]) -> bool:
    for used_start, used_end in used:
        if not (end <= used_start or start >= used_end):
            return True
    return False


def rewrite_cr_refs_in_body(
    content: str,
    *,
    node_type: str,
    item_path: str,
    target_resolved_path: str,
    cr_number: int,
    applied_version: int,
) -> str:
    """Replace ``target@~cr_number`` refs (as spelled in metadata) with ``target@applied_version``."""

    target = target_resolved_path.strip("/")
    if node_type != "config":
        return content
    from ..managers.config_validation import ConfigValidationManager
    from ..managers.tree.config_ops import _reference_strings_from_metadata

    validator = ConfigValidationManager(config_path=item_path, data_yaml=content)
    validator.parse()
    metadata = validator.metadata
    if not metadata.model_dump(exclude_none=True):
        return content
    base_folder = "/".join(item_path.strip("/").split("/")[:-1])
    replacements: list[tuple[str, str]] = []
    for ref_str in _reference_strings_from_metadata(metadata):
        raw = ref_str.strip()
        if not raw:
            continue
        suffix = ""
        if raw.endswith("?"):
            suffix = "?"
            raw = raw[:-1].strip()
        path_part, version_ref = parse_ref(raw)
        resolved = resolve_relative_path(base_folder, path_part).strip("/")
        if resolved != target:
            continue
        if not is_change_request_ref(version_ref):
            continue
        if change_request_number_from_ref(version_ref) != cr_number:
            continue
        new_ref = f"{path_part}@{applied_version}{suffix}"
        if new_ref != ref_str:
            replacements.append((ref_str, new_ref))
    used_spans: list[tuple[int, int]] = []
    edits: list[tuple[int, int, str]] = []
    for ref_str, new_ref in replacements:
        pattern = re.compile(rf"{_REF_ANCHOR_LOOKBEHIND}{re.escape(ref_str)}(?!\d)")
        chosen: re.Match[str] | None = None
        for match in pattern.finditer(content):
            if _ref_span_used(match.start(), match.end(), used_spans):
                continue
            if chosen is None or match.start() < chosen.start():
                chosen = match
        if chosen is None:
            continue
        used_spans.append((chosen.start(), chosen.end()))
        edits.append((chosen.start(), chosen.end(), new_ref))
    for start, end, new_ref in sorted(edits, key=lambda item: item[0], reverse=True):
        content = content[:start] + new_ref + content[end:]
    return content


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
