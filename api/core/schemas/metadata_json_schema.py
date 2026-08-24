"""JSON Schema export for the config metadata block (editor / autocomplete)."""

from __future__ import annotations

from typing import Any

from .cast_json_schema import enrich_cast_options_def
from .requests import ConfigOcmoMetadataSchema


def build_config_metadata_json_schema() -> dict[str, Any]:
    """
    Return JSON Schema for ``_ocmo`` metadata, enriched for editor autocomplete.

    Pydantic models ``cast.options`` and ``parameters`` as open maps at runtime;
    this export adds format-conditional option schemas and parameter value shapes.
    """
    schema = ConfigOcmoMetadataSchema.model_json_schema(mode="serialization")
    defs = schema.setdefault("$defs", {})
    enrich_cast_options_def(defs, "CastSchema")
    return schema
