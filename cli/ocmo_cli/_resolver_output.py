"""Print resolver tokens returned once on create or rotation."""

from __future__ import annotations

from typing import Any

from ._output import as_dict

_TOKEN_FIELDS = ("token1", "token")


def resolver_token_from_result(result: Any) -> str | None:
    """Return a full resolver token from a create/rotate API response."""
    if result is None:
        return None

    data = as_dict(result, fallback_vars=False)
    if not data:
        return None

    for key in _TOKEN_FIELDS:
        value = data.get(key)
        if isinstance(value, str) and value and not value.startswith("ocmo***"):
            return value
    return None


def print_resolver_token(result: Any) -> bool:
    """Print a resolver token to stdout when present. Returns whether anything was printed."""
    token = resolver_token_from_result(result)
    if not token:
        return False
    print(token)
    return True
