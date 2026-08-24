"""Output helpers for ``ocmo whoami``."""

from __future__ import annotations

from typing import Any

from ._output import as_dict


def whoami_table_row(data: Any) -> dict[str, Any]:
    """Flatten whoami API payload for table output."""
    payload = as_dict(data, fallback_vars=False)
    if not payload:
        return {}

    row: dict[str, Any] = {
        "auth_type": payload.get("auth_type"),
        "identifier": payload.get("identifier"),
        "display_name": payload.get("display_name"),
        "access_scope": payload.get("access_scope"),
    }

    user_details = payload.get("user_details")
    if isinstance(user_details, dict):
        row["email"] = user_details.get("email")
        row["is_global_admin"] = user_details.get("is_global_admin")
        row["claims"] = user_details.get("claims")
        return row

    resolver_details = payload.get("resolver_details")
    if isinstance(resolver_details, dict):
        row["namespace"] = resolver_details.get("namespace")
        row["name"] = resolver_details.get("name")
        row["token_number"] = resolver_details.get("token_number")

    return row


def whoami_table_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [whoami_table_row(item) for item in data]
    row = whoami_table_row(data)
    return [row] if row else []
