"""Shared Pydantic schemas for OCMO configuration documents."""

from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# OCMO path references (config, template, schema config, propagation target).
# Serialized as JSON Schema format "uri-reference" for editor autocomplete.
UriReference = Annotated[
    str,
    Field(
        min_length=1,
        json_schema_extra={"format": "uri-reference"},
        description=(
            "OCMO tree path with optional ``@version`` suffix "
            "(``latest``, ``stable``, custom tag, or integer). "
            "Relative paths use ``./`` and ``../`` from the current item's folder."
        ),
    ),
]

# JSONPath-like selector into config data or resolution context (not a tree path).
SelectorExpression = Annotated[
    str,
    Field(
        min_length=1,
        description="JSONPath-like selector expression (not an OCMO tree path).",
    ),
]

from .cast_options import CastFormat, validate_cast_options

_CAST_FORMATS = ("yaml", "json", "env", "hcl", "raw")

# Scalar values resolvers may pre-supply for dynamic parameters only.
DynamicParameterValue = str | int | float | bool

GlobPattern = Annotated[
    str,
    Field(
        min_length=1,
        max_length=512,
        description="Fnmatch-style glob matched against config paths (e.g. ``*/prod/**``).",
    ),
]

ShellHookCommand = Annotated[
    str,
    Field(
        min_length=1,
        max_length=4096,
        description=(
            "Shell command. Use ``{!conf}`` for resolved/placed file path(s); "
            "appended automatically when omitted from per-config hooks."
        ),
    ),
]


class CastSchema(BaseModel):
    """Cast format and validated per-format options."""

    model_config = ConfigDict(extra="forbid")

    format: CastFormat = Field(
        ...,
        description=(
            "Target output format for resolve results that are not already ``raw``. "
            "Priority: API ``?cast=`` → resolver ``cast`` → config ``_ocmo.cast`` → ``yaml``. "
            "The ``python`` format is SDK-only and cannot be set via REST."
        ),
        examples=["json"],
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Format-specific cast options (see resolving cast documentation)",
    )

    @model_validator(mode="after")
    def validate_options_for_format(self) -> CastSchema:
        object.__setattr__(
            self,
            "options",
            validate_cast_options(self.format, self.options),
        )
        return self


class ResolverCastSchema(CastSchema):
    """Default cast format applied to resolved output when the caller does not pass ``?cast=``."""


class ResolverConfigurationSchema(BaseModel):
    """Resolver service-account configuration (YAML subset of OCMO resolving behaviour).

    Stored on the Resolver tree item and applied to every resolve call authenticated
    with that resolver's token. See ``docs/features/resolvers.md`` (Resolver Configuration).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "title": "Resolver configuration",
            "description": (
                "Default cast format, dynamic parameter defaults, folder filters, "
                "and optional validation/post-resolve hooks for resolver-authenticated "
                "resolve calls."
            ),
        },
    )

    cast: ResolverCastSchema | None = Field(
        None,
        description=(
            "Default cast format for resolved output. Does not apply when the effective "
            "format is already ``raw`` (e.g. rendered template output)."
        ),
    )
    parameters: dict[str, DynamicParameterValue] = Field(
        default_factory=dict,
        description=(
            "Default values for **dynamic** parameters only. Keys must match parameter "
            "names declared in target configs. Cannot override ``projected`` or ``secret`` "
            "parameters. Callers may still override any value via ``?param_<name>=`` at resolve time."
        ),
        examples=[{"replicas": 5, "region": "eu-west-1"}],
    )
    include: list[GlobPattern] | None = Field(
        None,
        min_length=1,
        description=(
            "When resolving a folder, only process configs whose path matches one of these "
            "glob patterns. Mutually exclusive with ``exclude``."
        ),
        examples=[["*/prod/**", "*/staging/**"]],
    )
    exclude: list[GlobPattern] | None = Field(
        None,
        min_length=1,
        description=(
            "When resolving a folder, skip configs whose path matches any of these "
            "glob patterns. Mutually exclusive with ``include``."
        ),
        examples=[["**/draft/**", "**/deprecated/**"]],
    )
    validate: ShellHookCommand | None = Field(
        None,
        description=(
            "Shell command run on the target host **per** resolved config to verify output "
            "before placement. Use ``{!conf}`` for the resolved file path (appended if omitted). "
            "Mutually exclusive with ``validate_all``."
        ),
        examples=["nginx -t -c {!conf}"],
    )
    validate_all: ShellHookCommand | None = Field(
        None,
        description=(
            "Shell command run once after all configs in a folder resolve are written, "
            "receiving all output paths via ``{!conf}``. Mutually exclusive with ``validate``."
        ),
        examples=["check-all-configs {!conf}"],
    )
    post_resolve: ShellHookCommand | None = Field(
        None,
        description=(
            "Shell command run **per** config after successful validation and placement "
            "(CLI). Returned in the API response for non-CLI consumers. Use ``{!conf}`` "
            "for the placed file path. Mutually exclusive with ``post_resolve_all``."
        ),
        examples=["systemctl reload nginx"],
    )
    post_resolve_all: ShellHookCommand | None = Field(
        None,
        description=(
            "Shell command run once after all configs are placed in a folder resolve. "
            "Mutually exclusive with ``post_resolve``."
        ),
        examples=["systemctl daemon-reload && systemctl reload nginx"],
    )

    @field_validator("include", "exclude", mode="before")
    @classmethod
    def normalize_glob_list(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, str):
            return [value]
        return value

    @field_validator("include", "exclude")
    @classmethod
    def validate_glob_patterns(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            if not pattern or not pattern.strip():
                raise ValueError("Glob patterns must be non-empty strings")
        return patterns

    @field_validator("parameters")
    @classmethod
    def validate_parameter_names(cls, parameters: dict[str, DynamicParameterValue]) -> dict[str, DynamicParameterValue]:
        name_pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
        for name in parameters:
            if name == "omit":
                raise ValueError("Parameter name 'omit' is reserved (used by the {!omit} placeholder)")
            if not name_pattern.match(name):
                raise ValueError(
                    f"Invalid parameter name '{name}': must start with a letter or "
                    "underscore, then alphanumeric/underscore characters only"
                )
        return parameters

    @model_validator(mode="after")
    def validate_folder_filters(self) -> ResolverConfigurationSchema:
        if self.include is not None and self.exclude is not None:
            raise ValueError(
                "Resolver configuration cannot set both 'include' and 'exclude' (mutually exclusive folder filters)"
            )
        return self

    @model_validator(mode="after")
    def validate_validation_mode(self) -> ResolverConfigurationSchema:
        if self.validate is not None and self.validate_all is not None:
            raise ValueError("Resolver configuration cannot set both 'validate' and 'validate_all'")
        return self

    @model_validator(mode="after")
    def validate_post_resolve_mode(self) -> ResolverConfigurationSchema:
        if self.post_resolve is not None and self.post_resolve_all is not None:
            raise ValueError("Resolver configuration cannot set both 'post_resolve' and 'post_resolve_all'")
        return self
