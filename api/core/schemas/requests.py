from datetime import datetime
from typing import Any, ClassVar, Literal

import yaml
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from jinja2 import TemplateSyntaxError
from ninja import Schema
from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

from ..constants import PROBE_OPERATIONS, ParameterTransformer
from ..shortcuts import (
    assert_upload_size,
    make_template_environment,
    safe_yaml_load,
    validate_path_characters,
    validate_selector_syntax,
)
from ..validation_errors import format_pydantic_validation_error
from .generic import (
    CastSchema as ConfigCastSchema,
)
from .generic import (
    ResolverConfigurationSchema,
    SelectorExpression,
    UriReference,
)
from .propagation import ConfigPropagationSchema

_NAMESPACE_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"


class NamespaceCreateSchema(Schema):
    name: str = Field(
        ...,
        pattern=_NAMESPACE_NAME_PATTERN,
        min_length=1,
        max_length=100,
        description="Unique namespace identifier (alphanumeric, hyphens, underscores)",
        examples=["Apollo", "team-alpha"],
    )
    description: str = Field(
        "",
        max_length=4096,
        description="Human-readable namespace description",
        examples=["Configuration files related to Apollo project workloads"],
    )


class NamespacePatchSchema(Schema):
    name: str | None = Field(
        None,
        pattern=_NAMESPACE_NAME_PATTERN,
        min_length=1,
        max_length=100,
        description="New namespace name",
        examples=["Nova"],
    )
    description: str | None = Field(
        None,
        max_length=4096,
        description="Updated description. Markdown supported",
    )
    permissions_tag: str | None = None
    webhooks_tag: str | None = None
    git_sync_tag: str | None = None

    @model_validator(mode="after")
    def check_at_least_one(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided")
        return self


class DescribePayload(Schema):
    description: str = Field(
        ...,
        max_length=4096,
        description="Markdown description for the tree item",
        examples=["Primary database connection settings"],
    )


class LocationPayload(Schema):
    target_path: str = Field(
        ...,
        description="Destination path for move or copy",
        examples=["apps/backend/api"],
    )

    @field_validator("target_path")
    @classmethod
    def validate_target_path(cls, v: str) -> str:
        try:
            validate_path_characters(v.strip("/"))
        except DjangoValidationError as exc:
            raise ValueError(str(exc)) from exc
        return v


class TagPayload(Schema):
    tag: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_\.\+\-]+$",
        description="Only letters, numbers, and '_.+-' allowed",
        min_length=1,
        max_length=50,
        examples=["v1.0.0", "dev"],
    )
    version: int | None = Field(None, gt=0)


# ── Document uploads (raw body; validated RootModel[str]) ──


class DocumentRootModel(RootModel[str]):
    """Base for upload documents; coerces JSON object bodies to YAML text."""

    @field_validator("root", mode="before")
    @classmethod
    def align_document_type(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            return yaml.safe_dump(
                value,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )
        raise ValueError("Document body doesn't match the expected type")


class ConfigDocument(DocumentRootModel):
    """Config YAML document."""

    root: str = Field(
        ...,
        json_schema_extra={"format": "textarea"},
        description="Config YAML document",
        examples={
            "application/yaml": "foo: bar\nbaz: 42",
            "application/json": {"foo": "bar", "baz": 42},
            "application/octet-stream": "config.yaml",
        },
    )

    supported_types: ClassVar[list[str]] = [
        "application/yaml",
        "application/json",
        "application/octet-stream",
    ]
    document_name: ClassVar[str] = "config"

    @model_validator(mode="after")
    def validate_document(self):
        raw = self.root
        if not raw.strip():
            raise ValueError("Document content must not be empty")
        assert_upload_size(raw, settings.OCMO_MAX_CONFIG_UPLOAD_BYTES, "Config")
        try:
            safe_yaml_load(raw)
        except yaml.YAMLError as exc:
            raise ValueError("Payload is not valid YAML") from exc
        return self


class TemplateDocument(DocumentRootModel):
    """Jinja2 template source."""

    root: str = Field(
        ...,
        json_schema_extra={"format": "textarea"},
        description="Jinja2 template",
        examples={
            "text/plain": "foo:{{ bar }}\n",
            "text/x-jinja2": "foo: {{ bar }}\n",
            "application/octet-stream": "template.j2",
        },
    )
    supported_types: ClassVar[list[str]] = [
        "text/plain",
        "text/x-jinja2",
        "application/octet-stream",
    ]
    document_name: ClassVar[str] = "template"

    @model_validator(mode="after")
    def validate_document(self):
        raw = self.root
        if not raw.strip():
            raise ValueError("Document content must not be empty")
        assert_upload_size(raw, settings.OCMO_MAX_TEMPLATE_UPLOAD_BYTES, "Template")
        try:
            make_template_environment().parse(raw)
        except TemplateSyntaxError as exc:
            raise ValueError(f"Invalid Jinja2 syntax: {exc}") from exc
        return self


class SecretDocument(DocumentRootModel):
    """Secret credential document (YAML/JSON)."""

    root: str = Field(
        ...,
        json_schema_extra={"format": "textarea"},
        description="YAML (or JSON) credential document",
        examples={
            "application/yaml": "user: alice\npassword: s3cr3t",
            "application/json": {"user": "alice", "password": "s3cr3t"},
            "application/octet-stream": "secret.yaml",
        },
    )
    supported_types: ClassVar[list[str]] = [
        "application/yaml",
        "application/json",
        "application/octet-stream",
    ]
    document_name: ClassVar[str] = "secret"

    @model_validator(mode="after")
    def validate_document(self):
        raw = self.root
        if not raw.strip():
            raise ValueError("Document content must not be empty")
        assert_upload_size(raw, settings.OCMO_MAX_SECRET_UPLOAD_BYTES, "Secret")
        try:
            safe_yaml_load(raw)
        except yaml.YAMLError as exc:
            raise ValueError("Secret payload is not valid YAML") from exc
        return self


class ResolverDocument(DocumentRootModel):
    """Resolver configuration YAML."""

    root: str = Field(
        default="",
        json_schema_extra={"format": "textarea"},
        description="OCMO resolver configuration (YAML subset)",
        examples={
            "application/yaml": (
                "cast:\n"
                "  format: env\n"
                "  options:\n"
                "    type: unix\n"
                "    export: true\n"
                "parameters:\n"
                "  replicas: 3\n"
                "  region: us-east-1\n"
                "include:\n"
                '  - "*/prod/**"\n'
                'validate: "nginx -t -c {!conf}"\n'
                'post_resolve: "systemctl reload nginx"\n'
            ),
            "application/json": {
                "cast": {"format": "env", "options": {"type": "unix", "export": True}},
                "parameters": {"replicas": 3, "region": "us-east-1"},
                "include": ["*/prod/**"],
                "validate": "nginx -t -c {!conf}",
                "post_resolve": "systemctl reload nginx",
            },
            "application/octet-stream": "resolver-config.yaml",
        },
    )
    supported_types: ClassVar[list[str]] = [
        "application/yaml",
        "application/json",
        "application/octet-stream",
    ]
    document_name: ClassVar[str] = "resolver configuration"

    @model_validator(mode="after")
    def validate_document(self):
        raw = self.root
        if not raw.strip():
            return self
        try:
            data = safe_yaml_load(raw)
        except yaml.YAMLError as exc:
            raise ValueError("Resolver configuration is not valid YAML") from exc
        if data is None:
            return self
        if not isinstance(data, dict):
            raise ValueError("Resolver configuration must be a YAML mapping at the top level")
        try:
            ResolverConfigurationSchema.model_validate(data)
        except PydanticValidationError as exc:
            raise ValueError("; ".join(format_pydantic_validation_error(exc))) from exc
        except Exception as exc:
            raise ValueError(str(exc)) from exc
        return self


class ResolverRotateTokenPayload(Schema):
    """Body for resolver token rotation."""

    token_number: Literal[1, 2] = Field(
        ...,
        description="Which token slot to rotate (1 or 2)",
        examples=[1],
    )


# ── Tree locks ──


class LockPayload(Schema):
    """Body for creating or replacing a subtree lock."""

    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Human-readable rationale for the freeze",
        examples=["Production deployment freeze — release 2026-Q2"],
    )
    expires_at: datetime | None = Field(
        None,
        description="Optional UTC end time; lock expires automatically afterward",
    )


# ── Global Permissions ──


class GlobalPermissionActorSchema(BaseModel):
    model_config = {"extra": "forbid"}

    kind: Literal["User"]
    claims: dict[str, str]

    @model_validator(mode="after")
    def validate_actor(self):
        if not self.claims:
            raise ValueError("User actors require 'claims'")
        return self


class GlobalPermissionSectionSchema(BaseModel):
    model_config = {"extra": "forbid"}

    actors: list[GlobalPermissionActorSchema] = Field(..., min_length=1)


class GlobalPermissionRulePayload(Schema):
    id: str | None = None
    description: str | None = Field(None, max_length=500)
    namespace: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Namespace name glob pattern",
    )
    read: GlobalPermissionSectionSchema | None = None
    write: GlobalPermissionSectionSchema | None = None
    delete: GlobalPermissionSectionSchema | None = None
    audit: GlobalPermissionSectionSchema | None = None

    def to_rule_dict(self) -> dict:
        """Serialize to the dict shape stored in the database."""
        data = self.model_dump(exclude_none=True)
        for key in ("read", "write", "delete", "audit"):
            if key in data and data[key] is not None:
                data[key] = data[key]
        return data


class GlobalPermissionRuleMovePayload(Schema):
    position: float = Field(
        ...,
        description="New sort position for the rule (fractional values allowed between neighbors)",
        examples=[1.5],
    )


# ── Ocmo metadata schemas (used by resolving manager) ──

ExtendMode = Literal["accumulate", "distribute", "align"]
RenderMode = Literal["distribute", "align"]
ParameterType = Literal["projected", "dynamic", "secret"]


class ConfigExtendRefSchema(BaseModel):
    """One extend source config with optional slice (``key``) and remap (``as``)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    path: UriReference = Field(
        ...,
        description="Config path to merge (whole document when ``key`` is omitted).",
        examples=["../base-config@latest", "shared/all@stable"],
    )
    key: SelectorExpression | None = Field(
        None,
        description=(
            "Optional selector into the resolved source document; only that value is merged. "
            "Supports optional ``?`` suffix for soft missing keys."
        ),
        examples=[".database", ".services[0].name"],
    )
    as_: SelectorExpression | None = Field(
        None,
        alias="as",
        description=("Optional destination selector in the merge target; remaps the extracted ``key`` value."),
        examples=[".db", ".primary"],
    )

    @field_validator("key")
    @classmethod
    def validate_key_syntax(cls, v: str | None) -> str | None:
        if v is None:
            return v
        validate_selector_syntax(v)
        return v

    @field_validator("as_")
    @classmethod
    def validate_as_syntax(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v.endswith("?"):
            raise ValueError("Optional '?' suffix is only allowed on extend key selectors")
        validate_selector_syntax(v)
        return v


def normalize_extend_ref(ref: str | ConfigExtendRefSchema) -> ConfigExtendRefSchema:
    """Normalize a string or object extend reference."""

    if isinstance(ref, ConfigExtendRefSchema):
        return ref
    return ConfigExtendRefSchema(path=ref)


class ConfigExtendSchema(BaseModel):
    """`_ocmo.extend` block: merge other Configs into this one."""

    model_config = ConfigDict(extra="forbid")

    configs: list[UriReference | ConfigExtendRefSchema] = Field(
        ...,
        min_length=1,
        description=(
            "Source Config paths to merge, in order. Each entry is a path string or an object "
            "with ``path`` plus optional ``key`` / ``as`` slice/remap selectors."
        ),
        examples=[
            [
                "../base-config@latest",
                {"path": "shared/all@stable", "key": ".database"},
            ],
        ],
    )
    mode: ExtendMode = Field(
        "accumulate",
        description=(
            "``accumulate``: deep-merge all sources then this config. "
            "``distribute``: merge the value at ``by`` into each source document separately. "
            "``align``: pair list items at ``by`` with sources by index."
        ),
    )
    by: SelectorExpression | None = Field(
        None,
        description=(
            "JSONPath into this config's data (after ``_ocmo`` removal). "
            "Defaults to the document root. Required for ``align`` mode; meaning depends on ``mode``."
        ),
        examples=[".environments", ".services"],
    )

    @field_validator("configs", mode="before")
    @classmethod
    def cast_to_list(cls, v):
        return [v] if isinstance(v, str) else v

    @field_validator("configs")
    @classmethod
    def validate_configs_limit(
        cls, v: list[UriReference | ConfigExtendRefSchema]
    ) -> list[UriReference | ConfigExtendRefSchema]:
        limit = settings.OCMO_MAX_EXTEND_CONFIGS
        if len(v) > limit:
            raise ValueError(f"_ocmo.extend.configs cannot list more than {limit} config references")
        return v

    @model_validator(mode="after")
    def validate_align_by(self):
        if self.mode == "align" and not self.by:
            raise ValueError("extend mode 'align' requires the 'by' field")
        return self


class ConfigRenderSchema(BaseModel):
    """`_ocmo.render` block: render Jinja2 Templates using this Config's data."""

    model_config = ConfigDict(extra="forbid")

    templates: list[UriReference] = Field(
        ...,
        min_length=1,
        description=(
            "Template paths to render with this Config's resolved data as Jinja2 context. "
            "Supports ``@latest``, custom tags, and numeric version pins."
        ),
        examples=[["../templates/nginx.conf.j2@latest", "../templates/app.ini.j2"]],
    )
    mode: RenderMode = Field(
        "distribute",
        description=(
            "``distribute``: render each template once per element at ``by`` (or once for root data). "
            "``align``: pair list items at ``by`` with templates by index."
        ),
    )
    by: SelectorExpression | None = Field(
        None,
        description=(
            "JSONPath into config data selecting the rendering context or list to fan out. "
            "Omitted means the entire data document."
        ),
        examples=[".services"],
    )

    @field_validator("templates", mode="before")
    @classmethod
    def cast_to_list(cls, v):
        return [v] if isinstance(v, str) else v

    @field_validator("templates")
    @classmethod
    def validate_templates_limit(cls, v: list[str]) -> list[str]:
        limit = settings.OCMO_MAX_RENDER_TEMPLATES
        if len(v) > limit:
            raise ValueError(f"_ocmo.render.templates cannot list more than {limit} template references")
        return v

    @model_validator(mode="after")
    def validate_align_by(self):
        if self.mode == "align" and not self.by:
            raise ValueError("render mode 'align' requires the 'by' field")
        return self


class ConfigParameterSchema(BaseModel):
    """A single parameter declaration inside `_ocmo.parameters.<name>`."""

    model_config = ConfigDict(extra="forbid")

    type: ParameterType = Field(
        ...,
        description=(
            "``projected``: derive from config context (``.Name``, ``.Path``, ``.Data.*``, etc.). "
            "``dynamic``: caller-supplied at resolve time with ``value`` as default. "
            "``secret``: fetch from a Secret reference in ``value``."
        ),
    )
    value: Any = Field(
        ...,
        description=(
            "For ``projected``: selector expression (e.g. ``.Path[-1]``, ``.Data.labels.app``). "
            "For ``dynamic``: default scalar when the caller omits the parameter. "
            "For ``secret``: secret path reference "
            "``<path>[@version][:field.subfield]`` (relative paths allowed)."
        ),
        examples=[".Path[-1]", "production", "creds/db@stable:password"],
    )
    description: str = Field(
        ...,
        description="Human-readable description shown in UI and SDK introspection.",
        examples=["Last segment of the config path"],
    )
    transformers: list[ParameterTransformer] = Field(
        default_factory=list,
        description=(
            "Ordered transformers applied to the resolved value before substitution "
            "(string helpers and optional casts)."
        ),
    )

    @field_validator("transformers")
    @classmethod
    def validate_transformers_limit(cls, v: list[ParameterTransformer]) -> list[ParameterTransformer]:
        limit = settings.OCMO_MAX_PARAMETER_TRANSFORMERS
        if len(v) > limit:
            raise ValueError(f"Parameter cannot declare more than {limit} transformers")
        return v


class ConfigValidationSchema(BaseModel):
    """Reference to a Config that stores a JSON Schema document."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_path: UriReference = Field(
        ...,
        alias="schema",
        description=(
            "Path to a Config with ``_ocmo.is_json_schema: true``. "
            "Version suffix uses the same rules as extend/render references."
        ),
        examples=["schemas/my-app@stable", "./relative-schema@latest", "schemas/my-app"],
    )


class ConfigOcmoMetadataSchema(BaseModel):
    """Top-level `_ocmo` metadata block embedded in Config YAML."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "title": "_ocmo metadata",
            "description": (
                "OCMO resolution, validation, and propagation metadata embedded at the root of Config YAML."
            ),
        },
    )

    extend: ConfigExtendSchema | None = Field(
        None,
        description="Inherit and deep-merge data from one or more other Configs.",
    )
    render: ConfigRenderSchema | None = Field(
        None,
        description="Render Jinja2 Template(s) using this Config's resolved data as context.",
    )
    cast: ConfigCastSchema | None = Field(
        None,
        description=("Cast resolved output format (yaml, json, env, hcl, raw). Cannot be combined with ``render``."),
    )
    parameters: dict[str, ConfigParameterSchema] = Field(
        default_factory=dict,
        description=(
            "Parameters substituted at resolve time via ``{!name}`` placeholders "
            "in the config body (must be pre-declared)."
        ),
        examples=[
            {
                "replicas": {
                    "type": "dynamic",
                    "value": 3,
                    "description": "Replica count with default value `3` when the caller omits the parameter",
                },
                "app_name": {
                    "type": "projected",
                    "value": ".Data.labels.app",
                    "description": "Application name from config data",
                },
            },
        ],
    )
    name: str | None = Field(
        None,
        description=(
            "Override resolved output file name(s); may include characters not allowed "
            "in OCMO tree paths. Supports ``{!param}`` placeholders."
        ),
        examples=["nginx-deployment@prod.yaml", "{!env}/app.conf"],
    )
    validation: ConfigValidationSchema | None = Field(
        None,
        description="Reference a JSON Schema Config that validates this config's data on save.",
    )
    propagation: ConfigPropagationSchema | None = Field(
        None,
        description="Push merged data (or the whole document) to downstream target Configs.",
    )
    is_json_schema: bool | None = Field(
        False,
        description=("Mark this Config body as a JSON Schema document. Exclusive with all other ``_ocmo`` fields."),
    )

    def __bool__(self):
        return any(
            [
                self.extend,
                self.render,
                self.cast,
                self.parameters,
                self.name,
                self.validation,
                self.propagation,
                self.is_json_schema,
            ]
        )

    @field_validator("parameters")
    @classmethod
    def validate_parameter_names(cls, v):
        limit = settings.OCMO_MAX_CONFIG_PARAMETERS
        if len(v) > limit:
            raise ValueError(f"_ocmo.parameters cannot declare more than {limit} parameters")
        for name in v:
            if name == "omit":
                raise ValueError("Parameter name 'omit' is reserved (used by the {!omit} placeholder)")
            if not name or not name.replace("_", "").isalnum():
                raise ValueError(f"Invalid parameter name '{name}': must be alphanumeric with underscores")
        return v

    @model_validator(mode="after")
    def validate_render_cast(self):
        # Cast is incompatible with render (template output has no defined merge/cast format).
        if self.render is not None and self.cast is not None:
            raise ValueError(
                "_ocmo.cast cannot be used together with _ocmo.render "
                "(rendered output format is determined by the template)"
            )
        return self

    @model_validator(mode="after")
    def validate_name(self):
        if self.name is None:
            return self
        if self.name.startswith("/") or self.name.endswith("/"):
            raise ValueError("_ocmo.name cannot start or end with '/'")
        segments = self.name.split("/")
        if any(seg in (".", "..") for seg in segments):
            raise ValueError("_ocmo.name cannot contain '.' or '..' segments")
        if len(segments) > 5:
            raise ValueError("_ocmo.name cannot have more than 5 path segments")
        return self

    @model_validator(mode="after")
    def validate_json_schema_exclusive(self):
        if not self.is_json_schema:
            return self
        if any(
            [
                self.extend,
                self.render,
                self.cast,
                self.parameters,
                self.name,
                self.validation,
                self.propagation,
            ]
        ):
            raise ValueError("_ocmo.is_json_schema cannot be combined with other _ocmo fields")
        return self


class CanIRequestSchema(Schema):
    """Batch permission probe for frontend UI gating."""

    namespace: str | None = Field(
        None,
        pattern=_NAMESPACE_NAME_PATTERN,
        min_length=1,
        max_length=100,
        description="Target namespace for namespace-scoped and tree operations",
        examples=["project-alpha"],
    )
    operations: list[str] = Field(
        ...,
        min_length=1,
        description="Operations to probe, e.g. config:resolve, secret:tag, namespace:write",
        examples=[["config:resolve", "secret:tag", "namespace:write"]],
    )
    resource: str | None = Field(
        None,
        description="Tree path within the namespace; required for in-tree operations",
        examples=["apps/backend/api"],
    )

    @field_validator("operations")
    @classmethod
    def validate_operations(cls, values: list[str]) -> list[str]:
        unknown = [value for value in values if value not in PROBE_OPERATIONS]
        if unknown:
            raise ValueError(f"Unknown operation(s): {', '.join(unknown)}")
        return values
