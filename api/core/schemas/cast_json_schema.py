"""Shared JSON Schema enrichment for cast blocks (config metadata and resolver config)."""

from __future__ import annotations

from typing import Any

from .cast_options import cast_format_option_schemas, format_cast_options_json_schema


def merge_defs(target: dict[str, Any], source: dict[str, Any]) -> None:
    for name, value in source.get("$defs", {}).items():
        target.setdefault(name, value)


def enrich_cast_options_def(defs: dict[str, Any], cast_def_name: str) -> None:
    """Add format-conditional ``options`` schemas to a CastSchema-like $def."""
    cast = defs.get(cast_def_name)
    if not cast or not isinstance(cast, dict):
        return

    format_to_def: dict[str, str] = {}
    for format_name, model_cls in sorted(cast_format_option_schemas().items()):
        model_schema = format_cast_options_json_schema(format_name)
        merge_defs(defs, model_schema)
        def_name = model_cls.__name__
        defs.setdefault(
            def_name,
            {key: value for key, value in model_schema.items() if key != "$defs"},
        )
        format_to_def[format_name] = def_name

    properties = cast.setdefault("properties", {})
    properties["options"] = {
        "type": "object",
        "additionalProperties": False,
        "default": {},
        "description": (
            "Format-specific cast options (see resolving cast documentation). Applicable keys depend on ``format``."
        ),
    }

    cast.setdefault("allOf", []).extend(
        [
            {
                "if": {
                    "properties": {"format": {"const": format_name}},
                    "required": ["format"],
                },
                "then": {
                    "properties": {
                        "options": {"$ref": f"#/$defs/{def_name}"},
                    },
                },
            }
            for format_name, def_name in format_to_def.items()
        ]
    )
