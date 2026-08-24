"""Per-format cast option schemas (see docs/resolving-cast-feature.md)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CastFormat = Literal["yaml", "json", "env", "hcl", "raw"]
EnvCastDialect = Literal["unix", "windows", "powershell"]

# Coercion hints for query-string values (used by CastManager).
# TODO: replace by proper schema
CAST_OPTION_FIELD_TYPES: dict[str, dict[str, type]] = {
    "yaml": {
        "indent": int,
        "width": int,
        "flow_style": str,
        "sort_keys": bool,
        "default_scalar_style": str,
        "explicit_start": bool,
        "explicit_end": bool,
        "allow_unicode": bool,
        "trailing_newline": bool,
    },
    "json": {
        "indent": int,
        "sort_keys": bool,
        "ensure_ascii": bool,
        "allow_nan": bool,
        "separators": str,
        "trailing_newline": bool,
        "strict_keys": bool,
    },
    "env": {
        "type": str,
        "export": bool,
        "quote": str,
        "uppercase": bool,
        "lowercase": bool,
        "prefix": str,
        "separator": str,
        "list_format": str,
        "list_separator": str,
        "null_handling": str,
        "bool_format": str,
        "escape_newlines": bool,
        "sort_keys": bool,
        "strict": bool,
        "comment_header": bool,
    },
    "hcl": {
        "version": str,
        "indent": int,
        "block_style": str,
        "quote_keys": bool,
        "sort_keys": bool,
        "tfvars": bool,
        "heredoc_strings": bool,
        "trailing_newline": bool,
    },
    "raw": {
        "strict": bool,
        "stringify": bool,
        "encoding": str,
        "trailing_newline": bool,
        "strip": bool,
    },
}


class YamlCastOptionsSchema(BaseModel):
    """Options for ``cast.format: yaml``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "title": "YAML cast options",
            "description": "Emitter settings for YAML output after resolve.",
        },
    )

    indent: int = Field(
        default=2,
        ge=2,
        le=64,
        title="Indent",
        description="Block indentation width in spaces for mappings and sequences.",
        examples=[2, 4],
    )
    width: int = Field(
        default=0,
        ge=0,
        title="Line width",
        description="Soft line-wrap width in characters. Use 0 to disable wrapping.",
        examples=[0, 80, 120],
    )
    flow_style: Literal["block", "flow", "auto"] = Field(
        default="block",
        title="Flow style",
        description="Collection layout style: block (indented), flow (inline), or auto.",
        examples=["block"],
    )
    sort_keys: bool = Field(
        default=False,
        title="Sort keys",
        description="Sort mapping keys alphabetically when emitting output.",
        examples=[False, True],
    )
    default_scalar_style: Literal["'", '"', "|", ">"] | None = Field(
        default=None,
        title="Default scalar style",
        description=(
            "Force YAML scalar quoting style. Omit (null) to let the emitter choose "
            "automatically (literal block for multi-line strings)."
        ),
        examples=["|", ">"],
    )
    explicit_start: bool = Field(
        default=False,
        title="Explicit start",
        description="Emit a leading ``---`` document marker.",
        examples=[False],
    )
    explicit_end: bool = Field(
        default=False,
        title="Explicit end",
        description="Emit a trailing ``...`` document marker.",
        examples=[False],
    )
    allow_unicode: bool = Field(
        default=True,
        title="Allow Unicode",
        description="Allow non-ASCII characters unescaped in YAML output.",
        examples=[True],
    )
    trailing_newline: bool = Field(
        default=True,
        title="Trailing newline",
        description="Append a trailing newline at the end of output.",
        examples=[True],
    )


class JsonCastOptionsSchema(BaseModel):
    """Options for ``cast.format: json``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "title": "JSON cast options",
            "description": "Emitter settings for JSON output after resolve.",
        },
    )

    indent: int | None = Field(
        default=None,
        ge=0,
        le=32,
        title="Indent",
        description="Pretty-print with N-space indentation. Omit (null) for compact single-line JSON.",
        examples=[2, 4],
    )
    sort_keys: bool = Field(
        default=False,
        title="Sort keys",
        description="Sort object keys alphabetically when emitting output.",
        examples=[False, True],
    )
    ensure_ascii: bool = Field(
        default=False,
        title="Ensure ASCII",
        description="Escape non-ASCII characters as ``\\uXXXX`` in JSON output.",
        examples=[False],
    )
    allow_nan: bool = Field(
        default=False,
        title="Allow NaN",
        description="Permit NaN and Infinity values (non-standard JSON).",
        examples=[False],
    )
    separators: Literal["auto", "compact", "pretty"] = Field(
        default="auto",
        title="Separators",
        description="Separator style between keys and values: auto, compact (`,`:), or pretty (`, `:).",
        examples=["auto", "pretty"],
    )
    trailing_newline: bool = Field(
        default=False,
        title="Trailing newline",
        description="Append a trailing newline at the end of output.",
        examples=[False, True],
    )
    strict_keys: bool = Field(
        default=False,
        title="Strict keys",
        description="Reject non-string mapping keys in JSON output.",
        examples=[False, True],
    )


class EnvCastOptionsSchema(BaseModel):
    """Options for ``cast.format: env``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "title": "Environment cast options",
            "description": "Flatten resolved data into shell environment variable assignments.",
        },
    )

    type: EnvCastDialect = Field(
        default="unix",
        title="Dialect",
        description="Shell dialect: unix (bash), windows (cmd), or powershell.",
        examples=["unix", "powershell"],
    )
    export: bool = Field(
        default=True,
        title="Export",
        description="Prefix Unix/bash entries with ``export``. Ignored for other dialects.",
        examples=[True, False],
    )
    quote: Literal["auto", "always", "single", "double", "never"] = Field(
        default="auto",
        title="Quote mode",
        description="Quoting strategy for variable values: auto, always, single, double, or never.",
        examples=["auto", "single"],
    )
    uppercase: bool = Field(
        default=False,
        title="Uppercase names",
        description="Convert variable names to UPPERCASE.",
        examples=[False, True],
    )
    lowercase: bool = Field(
        default=False,
        title="Lowercase names",
        description="Convert variable names to lowercase. Mutually exclusive with uppercase.",
        examples=[False],
    )
    prefix: str = Field(
        default="",
        max_length=256,
        title="Name prefix",
        description="String prepended to every environment variable name.",
        examples=["", "APP_"],
    )
    separator: str = Field(
        default="_",
        max_length=16,
        title="Key separator",
        description="Separator inserted between nested keys when flattening to env names.",
        examples=["_", "."],
    )
    list_format: Literal["indexed", "joined", "json", "space"] = Field(
        default="indexed",
        title="List format",
        description=(
            "How lists are represented: indexed (``key_0``, ``key_1``), joined (single value), "
            "json, or space-separated."
        ),
        examples=["indexed", "joined"],
    )
    list_separator: str = Field(
        default=",",
        max_length=16,
        title="List separator",
        description="Separator used when ``list_format`` is ``joined``.",
        examples=[",", "|"],
    )
    null_handling: Literal["skip", "empty", "literal"] = Field(
        default="skip",
        title="Null handling",
        description="How null values are emitted: skip (omit), empty (``KEY=``), or literal (``KEY=null``).",
        examples=["skip", "empty"],
    )
    bool_format: Literal["lower", "upper", "numeric", "yesno", "onoff"] = Field(
        default="lower",
        title="Boolean format",
        description="Boolean literal style: lower, upper, numeric, yesno, or onoff.",
        examples=["lower", "numeric"],
    )
    escape_newlines: bool = Field(
        default=True,
        title="Escape newlines",
        description="Replace newlines in string values with the literal ``\\n`` sequence.",
        examples=[True],
    )
    sort_keys: bool = Field(
        default=False,
        title="Sort keys",
        description="Sort emitted variable names alphabetically.",
        examples=[False, True],
    )
    strict: bool = Field(
        default=True,
        title="Strict names",
        description=(
            "Fail when a flattened variable name is not ``[A-Za-z_][A-Za-z0-9_]*``. "
            "When false, invalid characters are sanitized."
        ),
        examples=[True, False],
    )
    comment_header: bool = Field(
        default=False,
        title="Comment header",
        description="Emit a leading comment with the source config path and version.",
        examples=[False, True],
    )

    @model_validator(mode="after")
    def validate_name_case(self) -> EnvCastOptionsSchema:
        if self.uppercase and self.lowercase:
            raise ValueError("env cast options cannot set both 'uppercase' and 'lowercase'")
        return self


class HclCastOptionsSchema(BaseModel):
    """Options for ``cast.format: hcl``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "title": "HCL cast options",
            "description": "Emitter settings for HashiCorp Configuration Language output.",
        },
    )

    version: Literal["1", "2"] = Field(
        default="2",
        title="HCL version",
        description="HCL syntax version to emit.",
        examples=["2"],
    )
    indent: int = Field(
        default=2,
        ge=0,
        le=16,
        title="Indent",
        description="Indentation width in spaces for nested blocks and collections.",
        examples=[2],
    )
    block_style: Literal["attribute", "block"] = Field(
        default="attribute",
        title="Block style",
        description="Top-level emission style: attribute (``x = { ... }``) or block (``x { ... }``).",
        examples=["attribute", "block"],
    )
    quote_keys: bool = Field(
        default=False,
        title="Quote keys",
        description="Always quote attribute keys (required when keys contain special characters).",
        examples=[False, True],
    )
    sort_keys: bool = Field(
        default=False,
        title="Sort keys",
        description="Sort mapping keys alphabetically when emitting output.",
        examples=[False, True],
    )
    tfvars: bool = Field(
        default=False,
        title="Terraform tfvars",
        description="Emit ``terraform.tfvars`` style top-level assignments without enclosing blocks.",
        examples=[False, True],
    )
    heredoc_strings: bool = Field(
        default=False,
        title="Heredoc strings",
        description="Emit multi-line string values as HCL heredocs (``<<-EOT``).",
        examples=[False, True],
    )
    trailing_newline: bool = Field(
        default=True,
        title="Trailing newline",
        description="Append a trailing newline at the end of output.",
        examples=[True],
    )


class RawCastOptionsSchema(BaseModel):
    """Options for ``cast.format: raw``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "title": "Raw cast options",
            "description": "Return resolved data as a plain text scalar without structural formatting.",
        },
    )

    strict: bool = Field(
        default=True,
        title="Strict scalar",
        description="Require a scalar value at the document root. Raise when the resolved value is a mapping or list.",
        examples=[True, False],
    )
    stringify: bool = Field(
        default=False,
        title="Stringify",
        description="When strict is false, YAML-dump non-scalar values instead of failing.",
        examples=[False, True],
    )
    encoding: str = Field(
        default="utf-8",
        max_length=32,
        title="Encoding",
        description="Text encoding label for raw output (informational for file writers).",
        examples=["utf-8"],
    )
    trailing_newline: bool = Field(
        default=False,
        title="Trailing newline",
        description="Append a trailing newline at the end of output.",
        examples=[False, True],
    )
    strip: bool = Field(
        default=False,
        title="Strip whitespace",
        description="Strip leading and trailing whitespace from the scalar value.",
        examples=[False, True],
    )


_CAST_OPTIONS_SCHEMAS: dict[CastFormat, type[BaseModel]] = {
    "yaml": YamlCastOptionsSchema,
    "json": JsonCastOptionsSchema,
    "env": EnvCastOptionsSchema,
    "hcl": HclCastOptionsSchema,
    "raw": RawCastOptionsSchema,
}


CAST_FORMATS = frozenset(_CAST_OPTIONS_SCHEMAS.keys())

_CAST_OPTION_UI_RULES: dict[str, dict[str, dict[str, Any]]] = {
    "env": {
        "uppercase": {"x-ocmo-incompatible-with": ["lowercase"]},
        "lowercase": {"x-ocmo-incompatible-with": ["uppercase"]},
        "export": {"x-ocmo-enabled-when": {"type": "unix"}},
        "list_separator": {"x-ocmo-enabled-when": {"list_format": "joined"}},
    },
}


def _apply_cast_option_ui_rules(format_name: str, properties: dict[str, Any]) -> dict[str, Any]:
    rules = _CAST_OPTION_UI_RULES.get(format_name, {})
    enriched: dict[str, Any] = {}
    for key, prop in properties.items():
        if not isinstance(prop, dict):
            enriched[key] = prop
            continue
        merged = dict(prop)
        merged.update(rules.get(key, {}))
        enriched[key] = merged
    return enriched


def _simplify_optional_property(prop: dict[str, Any]) -> dict[str, Any]:
    """Flatten ``anyOf[T, null]`` into a single property schema for API consumers."""
    any_of = prop.get("anyOf")
    if not isinstance(any_of, list):
        return prop

    non_null = [item for item in any_of if item != {"type": "null"}]
    if len(non_null) != 1:
        return prop

    simplified = dict(non_null[0])
    for key in ("title", "description", "default", "examples"):
        if key in prop and key not in simplified:
            simplified[key] = prop[key]
    return simplified


def format_cast_options_json_schema(format_name: str) -> dict[str, Any]:
    """Return a JSON Schema document for one cast format's options."""
    schema_cls = _CAST_OPTIONS_SCHEMAS[format_name]  # type: ignore[index]
    schema = schema_cls.model_json_schema(mode="serialization")
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        schema["properties"] = _apply_cast_option_ui_rules(
            format_name,
            {
                key: _simplify_optional_property(value) if isinstance(value, dict) else value
                for key, value in properties.items()
            },
        )
    return schema


def validate_cast_options(format_name: str, options: Any) -> dict[str, Any]:
    """Validate and normalize cast options for ``format_name``."""
    if format_name not in _CAST_OPTIONS_SCHEMAS:
        raise ValueError(f"Unknown cast format {format_name!r}")
    raw = {} if options is None else options
    if not isinstance(raw, dict):
        raise ValueError("cast.options must be a mapping")
    schema = _CAST_OPTIONS_SCHEMAS[format_name]  # type: ignore[index]
    validated = schema.model_validate(raw)
    return validated.model_dump(exclude_none=True, exclude_defaults=True)


def cast_format_option_schemas() -> dict[str, type[BaseModel]]:
    """Return per-format Pydantic option schemas (for API introspection)."""
    return dict(_CAST_OPTIONS_SCHEMAS)
