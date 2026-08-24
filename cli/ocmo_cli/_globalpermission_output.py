"""Output helpers for global permission rules."""

from __future__ import annotations

from typing import Any

from ._output import as_dict, sanitize_for_output

_PERMISSION_SECTIONS = ("read", "write", "delete", "audit")


def _format_actor_claims(claims: dict[str, Any]) -> str:
    """Format one actor block: claim constraints are combined with AND."""
    parts = [f"{key}={claims[key]}" for key in sorted(claims) if claims[key] is not None]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return " AND ".join(parts)


def format_section_claims(section: Any) -> str:
    """Format one permission section with AND inside actors and OR between actors."""
    if section is None:
        return ""
    payload = as_dict(section, fallback_vars=False)
    if not isinstance(payload, dict):
        return ""
    actors = payload.get("actors")
    if not isinstance(actors, list):
        return ""

    blocks: list[str] = []
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        claims = actor.get("claims")
        if not isinstance(claims, dict):
            continue
        block = _format_actor_claims(claims)
        if block:
            blocks.append(block)

    if not blocks:
        return ""
    if len(blocks) == 1:
        return blocks[0]

    formatted_blocks: list[str] = []
    for block in blocks:
        if " AND " in block:
            formatted_blocks.append(f"({block})")
        else:
            formatted_blocks.append(block)
    return " OR ".join(formatted_blocks)


def global_permission_table_row(row: dict[str, Any], *, wide: bool = False) -> dict[str, Any]:
    """Flatten rule payload fields used by ``ocmo get gp`` output."""
    rule = as_dict(row.get("rule"), fallback_vars=False)
    flat = dict(row)
    flat["namespace"] = rule.get("namespace", "")
    rule_id = rule.get("id")
    if rule_id not in (None, ""):
        flat["id"] = str(rule_id)
    elif flat.get("id") is not None:
        flat["id"] = str(flat["id"])
    if wide:
        for section in _PERMISSION_SECTIONS:
            flat[section] = format_section_claims(rule.get(section))
        flat.pop("rule", None)
    return flat


def global_permission_table_rows(
    rows: list[dict[str, Any]],
    *,
    wide: bool = False,
) -> list[dict[str, Any]]:
    return [global_permission_table_row(row, wide=wide) for row in rows]


def emit_get_globalpermission_output(
    data: Any,
    *,
    output_fmt: str | None = None,
    ctx_fmt: str | None = None,
) -> None:
    """Emit one rule like ``ocmo get globalpermission ADDRESS``."""
    from ._output_manifest import emit_command_output

    payload = sanitize_for_output(as_dict(data, fallback_vars=False) or data)
    emit_command_output(
        "get globalpermission",
        payload,
        output_fmt,
        ctx_fmt=ctx_fmt,
    )
