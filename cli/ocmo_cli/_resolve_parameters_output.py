"""Output helpers for ``ocmo resolve parameters``."""

from __future__ import annotations

from typing import Any

from ._output import as_dict


def parameter_config_value(param: dict[str, Any]) -> Any:
    """Value as declared in the ocmo configuration (type-specific)."""
    ptype = param.get("type") or ""
    if ptype == "projected":
        return param.get("selector")
    if ptype == "dynamic":
        return param.get("declared_default")
    if ptype == "secret":
        return param.get("secret_reference")
    return None


def parameter_resolved_value(param: dict[str, Any]) -> Any:
    """Effective value after evaluation, transformers, and secret masking."""
    return param.get("effective_value")


def filter_parameters_data(data: Any, types: tuple[str, ...]) -> Any:
    """Return payload with ``parameters`` filtered to the given types (CLI-side)."""
    if not types:
        return data

    type_set = {item.lower() for item in types}
    payload = as_dict(data, fallback_vars=False)
    if not payload:
        return data

    parameters = payload.get("parameters") or {}
    if not isinstance(parameters, dict):
        return data

    filtered = {
        name: parameters[name]
        for name in parameters
        if (as_dict(parameters[name], fallback_vars=False).get("type") or "").lower() in type_set
    }
    return {**payload, "parameters": filtered}


def resolve_parameters_table_rows(data: Any) -> list[dict[str, Any]]:
    """Flatten resolve-parameters API payload into table rows."""
    payload = as_dict(data, fallback_vars=False)
    parameters = payload.get("parameters") or {}
    if not isinstance(parameters, dict):
        return []

    rows: list[dict[str, Any]] = []
    for name in sorted(parameters):
        param = as_dict(parameters[name], fallback_vars=False)
        transformers = param.get("transformers_applied") or []
        if not isinstance(transformers, list):
            transformers = []
        rows.append(
            {
                "name": name,
                "type": param.get("type") or "",
                "value": parameter_config_value(param),
                "resolved_value": parameter_resolved_value(param),
                "description": param.get("description") or "",
                "transformers": ", ".join(str(item) for item in transformers),
            }
        )
    return rows
