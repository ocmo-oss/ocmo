"""Recursive deep merge with extend semantics and {!omit} handling."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..constants.resolve import OMIT
from ..exceptions import ConfigExtendNotPossible
from ..shortcuts import is_mapping, to_plain


def all_int_keys(mapping: Mapping[Any, Any]) -> bool:
    if not mapping:
        return False
    for k in mapping.keys():
        if isinstance(k, bool):
            return False
        if isinstance(k, int):
            continue
        if isinstance(k, str) and k.lstrip("-").isdigit():
            continue
        return False
    return True


def apply_list_directives(base_list: list, directives: Mapping[Any, Any]) -> list:
    """Update a list by integer-keyed dict directives (merge / append / prepend)."""
    result = list(base_list)
    for key, value in directives.items():
        idx = int(key)
        if idx < 0:
            result.insert(0, value)
        elif idx >= len(result):
            result.append(value)
        else:
            existing = result[idx]
            if is_mapping(existing) and is_mapping(value):
                result[idx] = deep_merge(existing, value, level=1)
            else:
                result[idx] = value
    return result


def deep_merge(base: Any, updater: Any, level: int = 0) -> Any:
    """Recursive deep merge with the extend semantics from the design."""
    if updater is OMIT:
        return OMIT

    base_plain = to_plain(base)
    updater_plain = to_plain(updater)

    if isinstance(base_plain, list) and isinstance(updater_plain, dict) and all_int_keys(updater_plain):
        merged_list = apply_list_directives(base_plain, updater_plain)
        return [x for x in merged_list if x is not OMIT]

    if type(base_plain) is not type(updater_plain):
        if level == 0:
            raise ConfigExtendNotPossible(
                "Cannot extend documents of different root types: "
                f"base={type(base_plain).__name__} "
                f"updater={type(updater_plain).__name__}"
            )
        return updater_plain

    if isinstance(updater_plain, (dict, list)) and not updater_plain:
        return base_plain if level == 0 else updater_plain

    if isinstance(base_plain, dict):
        merged: dict[Any, Any] = dict(base_plain)
        for key, value in updater_plain.items():
            if value is OMIT:
                merged.pop(key, None)
                continue
            if key in merged:
                merged[key] = deep_merge(merged[key], value, level + 1)
            else:
                merged[key] = value
        return merged

    if isinstance(base_plain, list):
        return [*base_plain, *updater_plain]

    return updater_plain


def strip_omit(value: Any) -> Any:
    """Remove ``OMIT`` sentinels left over from substitution."""
    if value is OMIT:
        return None
    if isinstance(value, dict):
        return {k: strip_omit(v) for k, v in value.items() if v is not OMIT}
    if isinstance(value, list):
        return [strip_omit(v) for v in value if v is not OMIT]
    return value
