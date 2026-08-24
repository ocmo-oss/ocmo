"""JSON Schema export for resolver configuration (editor / autocomplete)."""

from __future__ import annotations

from typing import Any

from .cast_json_schema import enrich_cast_options_def
from .generic import ResolverConfigurationSchema

_PARAMETER_NAME_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"


def _enrich_parameters(schema: dict[str, Any]) -> None:
    parameters = schema.get("properties", {}).get("parameters")
    if not parameters or not isinstance(parameters, dict):
        return

    parameters["propertyNames"] = {
        "pattern": _PARAMETER_NAME_PATTERN,
        "description": ("Dynamic parameter name (alphanumeric and underscore; cannot be ``omit``)."),
    }
    parameters["additionalProperties"] = {
        "anyOf": [
            {"type": "string"},
            {"type": "integer"},
            {"type": "number"},
            {"type": "boolean"},
        ],
        "description": (
            "Default value for a dynamic parameter declared in target configs. "
            "Cannot override projected or secret parameters."
        ),
    }


def _enrich_glob_arrays(schema: dict[str, Any]) -> None:
    for key in ("include", "exclude"):
        field = schema.get("properties", {}).get(key)
        if not field or not isinstance(field, dict):
            continue
        branches = field.get("anyOf")
        if not isinstance(branches, list):
            continue
        for branch in branches:
            if branch.get("type") != "array":
                continue
            items = branch.setdefault("items", {})
            if isinstance(items, dict):
                items.setdefault("minLength", 1)
                items.setdefault(
                    "description",
                    "Fnmatch-style glob matched against config paths within the resolved folder.",
                )


def build_resolver_configuration_json_schema() -> dict[str, Any]:
    """
    Return JSON Schema for resolver configuration YAML, enriched for editor autocomplete.
    """
    schema = ResolverConfigurationSchema.model_json_schema(mode="serialization")
    defs = schema.setdefault("$defs", {})
    enrich_cast_options_def(defs, "ResolverCastSchema")
    _enrich_parameters(schema)
    _enrich_glob_arrays(schema)
    return schema
