import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, Optional

from ninja import Schema
from pydantic import ConfigDict, Field

from ..exceptions import VersionNotFound
from ..managers.resolver_tokens import ResolverTokenManager
from ..shortcuts import is_valid_positive_int, mask_resolver_token


class UserWhoAmIDetails(Schema):
    """OIDC-specific identity fields."""

    email: Any | None = Field(
        default=None,
        description="OIDC email claim",
        examples=["dev@localhost"],
    )
    is_global_admin: bool = Field(
        ...,
        description="Whether the user matches OIDC global-admin claim/value",
    )
    claims: dict[str, Any] = Field(
        default_factory=dict,
        description="All OIDC JWT claims (excluding internal fields)",
    )


class ResolverWhoAmIDetails(Schema):
    """Resolver service-account fields."""

    namespace: str = Field(..., description="Namespace name")
    name: str = Field(..., description="Resolver leaf name")
    token_number: int = Field(..., description="Which resolver token (1 or 2) authenticated the request")


class UserWhoAmISchema(Schema):
    """Authenticated OIDC user identity."""

    auth_type: Literal["user"] = Field(
        ...,
        description="Authentication method: OIDC user",
    )
    identifier: Any = Field(
        ...,
        description="OIDC subject or configured user id claim",
        examples=["dev-admin"],
    )
    display_name: Any = Field(
        ...,
        description="Human-readable identity label",
        examples=["Dev Admin"],
    )
    access_scope: str = Field(
        default="",
        description="Subtree scope for tree operations; empty for OIDC users",
    )
    user_details: UserWhoAmIDetails = Field(
        ...,
        description="OIDC user claims and flags",
    )


class ResolverWhoAmISchema(Schema):
    """Authenticated resolver service-account identity."""

    auth_type: Literal["resolver"] = Field(
        ...,
        description="Authentication method: resolver service account",
    )
    identifier: Any = Field(
        ...,
        description="Full resolver tree path (<access_scope>/<name>)",
        examples=["app/my-resolver"],
    )
    display_name: Any = Field(
        ...,
        description="Human-readable identity label",
        examples=["Resolver (app/my-resolver)"],
    )
    access_scope: str = Field(
        ...,
        description="Resolver subtree scope path",
        examples=["app"],
    )
    resolver_details: ResolverWhoAmIDetails = Field(
        ...,
        description="Resolver token metadata",
    )


WhoAmISchema = Annotated[
    UserWhoAmISchema | ResolverWhoAmISchema,
    Field(discriminator="auth_type"),
]


class CanIResponseSchema(Schema):
    """Per-operation permission probe results."""

    allowed: dict[str, bool] = Field(
        ...,
        description="Whether each requested operation is allowed for the current identity",
        examples=[{"config:resolve": True, "secret:tag": False}],
    )


class NamespaceSchema(Schema):
    name: str
    description: str
    permissions_tag: str
    webhooks_tag: str
    git_sync_tag: str
    created_at: datetime
    updated_at: datetime


class ErrorSchema(Schema):
    error: str | list
    audit_event_id: uuid.UUID | None = Field(
        default=None,
        description="Audit log event ID when the failure was recorded server-side",
    )


class InfoSchema(Schema):
    details: str


class HealthCheckSchema(Schema):
    status: Literal["ok", "error"]
    message: str | None = Field(
        default=None,
        description="Error detail when status is error",
    )


class HealthSchema(Schema):
    status: Literal["ok", "error"] = Field(
        ...,
        description="Overall health: ok when all checks pass",
    )
    checks: dict[str, HealthCheckSchema] = Field(
        ...,
        description="Per-component health results",
    )


class PublicOidcAuthSchema(Schema):
    """Browser-facing OIDC settings for interactive clients (SPA, CLI auth code flow)."""

    issuer: str = Field(
        ...,
        description="OIDC issuer URL (authority for discovery)",
        examples=["http://localhost:8080/dex"],
    )
    client_id: str = Field(
        ...,
        description="OAuth2 client id for the browser SPA and interactive CLI device login",
        examples=["ocmo-api"],
    )
    authorization_url: str = Field(
        ...,
        description="OAuth2 authorization endpoint",
        examples=["http://localhost:8080/dex/auth"],
    )
    token_url: str = Field(
        ...,
        description="OAuth2 token endpoint",
        examples=["http://localhost:8080/dex/token"],
    )
    scopes: str = Field(
        ...,
        description="Space-separated OAuth2 scopes requested by OCMO clients",
        examples=["openid profile email groups"],
    )


class PublicAuthSchema(Schema):
    """Public OIDC settings for frontend, SDK, and CLI bootstrap."""

    oidc: PublicOidcAuthSchema = Field(
        ...,
        description="Browser-facing OIDC client configuration",
    )


class BuiltinNamespacePathsSchema(Schema):
    config: list[str] = Field(
        ...,
        description="Built-in namespace config paths (e.g. _permissions)",
        examples=[["_permissions", "_webhooks", "_git_sync"]],
    )
    secret: list[str] = Field(
        ...,
        description="Built-in namespace secret paths",
        examples=[["_webhooks_secret", "_git_sync_secret"]],
    )
    schema: list[str] = Field(
        ...,
        description="Built-in namespace schema config paths",
        examples=[["_permissions.schema", "_webhooks.schema", "_git_sync.schema"]],
    )
    order: list[str] = Field(
        ...,
        description="Preferred display order for built-in namespace items in the tree",
    )


class ReservedTagsSchema(Schema):
    config: list[str] = Field(
        ...,
        description="Reserved tag names for configs",
        examples=[["latest", "stable"]],
    )
    template: list[str] = Field(
        ...,
        description="Reserved tag names for templates",
        examples=[["latest"]],
    )
    secret: list[str] = Field(
        ...,
        description="Reserved tag names for secrets",
        examples=[["latest"]],
    )


class ProductVersionSchema(Schema):
    model_config = ConfigDict(ser_json_exclude_none=True)

    product: Literal["ocmo"] = Field(
        ...,
        description="Product identifier",
        examples=["ocmo"],
    )
    version: str = Field(
        ...,
        description="Deployed package version",
        examples=["0.8.19"],
    )
    license: str = Field(
        ...,
        description="SPDX license identifier",
        examples=["Apache-2.0"],
    )
    license_name: str = Field(
        ...,
        description="Human-readable license name",
        examples=["Apache License, Version 2.0"],
    )
    config_metadata_key: str = Field(
        ...,
        description="Top-level YAML key for OCMO config metadata (e.g. _ocmo)",
        examples=["_ocmo"],
    )
    builtin_namespace_paths: BuiltinNamespacePathsSchema = Field(
        ...,
        description="Built-in namespace tree paths created for every namespace",
    )
    reserved_tags: ReservedTagsSchema = Field(
        ...,
        description="Reserved version tag names that cannot be set via the tag API",
    )
    auth: PublicAuthSchema = Field(
        ...,
        description="Public authentication configuration for frontend, SDK, and CLI bootstrap",
    )


class ProductVersionWithNoticeSchema(ProductVersionSchema):
    notice: str | None = Field(
        default=None,
        description="Product NOTICE text; included when ``?notice=true``",
    )


class NamespaceDeletedSchema(Schema):
    """Confirmation payload for a successful namespace deletion."""

    success: Literal[True] = Field(
        True,
        description="Deletion completed successfully",
    )
    namespace: str = Field(
        ...,
        description="Canonical name of the namespace that was removed",
    )


class DeleteSchema(Schema):
    delete: list[str]


class CopiedItemsSchema(Schema):
    created: list[str]


class TreeNavigationNodeSchema(Schema):
    """Minimal tree node metadata for navigate/search (UI tree browser)."""

    name: str = Field(..., description="Leaf segment name")
    path: str = Field(..., description="Full path within the namespace")
    node_type: str = Field(..., description="Item type discriminator")


class BaseNodeSchema(Schema):
    name: str = Field(..., description="Leaf segment name")
    path: str = Field(..., description="Full path within the namespace")
    node_type: str = Field(..., description="Item type discriminator")
    author: str = Field(..., description="Last author identifier")
    description: str = Field(..., description="Markdown description")


class FolderSchema(BaseNodeSchema):
    node_type: Literal["folder"]
    created_at: datetime = Field(..., description="Creation timestamp")


class ConfigSchema(BaseNodeSchema):
    node_type: Literal["config"]
    tags: dict[str, int]


class TemplateSchema(BaseNodeSchema):
    node_type: Literal["template"]
    tags: dict[str, int]


class SecretSchema(BaseNodeSchema):
    node_type: Literal["secret"]
    tags: dict[str, int]


class VersionSchema(Schema):
    version: str | int
    tags: list[str]
    data: str
    updater: str
    updated_at: datetime
    deleted_at: datetime | None


def _resolve_version_data(obj, tags_field="tags", version_model=None):
    """Shared logic for resolving version data for Config and Template."""
    tags_per_version = {}
    for tag, ver in obj.tags.items():
        tags_per_version.setdefault(ver, []).append(tag)

    requested_version = getattr(obj, "_requested_version", "latest")

    if is_valid_positive_int(requested_version):
        requested_version = int(requested_version)
    else:
        resolved = obj.tags.get(requested_version)
        if resolved is None:
            raise VersionNotFound("Specified tag wasn't found")
        requested_version = resolved

    if requested_version != "latest":
        version_obj = obj.versions.filter(
            version=requested_version,
            deleted_at__isnull=True,
        ).first()
        if not version_obj:
            raise VersionNotFound("Specified version wasn't found")
    else:
        version_obj = obj.versions.order_by("-version").first()

    version_obj.tags = tags_per_version.get(version_obj.version, [])
    return version_obj


class SecretVersionSchema(Schema):
    version: str | int
    tags: list[str]
    updater: str
    updated_at: datetime
    deleted_at: datetime | None
    data: str | None = None


class ConfigSchemaExtended(ConfigSchema):
    version_data: VersionSchema
    propagation: Optional["PropagationResultSchema"] = None

    @staticmethod
    def resolve_version_data(obj, context):
        return _resolve_version_data(obj)

    @staticmethod
    def resolve_propagation(obj, context):
        return getattr(obj, "_propagation_result", None)


class PropagationTargetResult(Schema):
    path: str
    status: Literal["updated", "unchanged", "skipped", "error"]
    version: int | None = None
    reason: str | None = None


class PropagationResultSchema(Schema):
    source_path: str
    source_version: int
    trigger: str
    targets: list[PropagationTargetResult]


class TemplateSchemaExtended(TemplateSchema):
    version_data: VersionSchema

    @staticmethod
    def resolve_version_data(obj, context):
        return _resolve_version_data(obj)


class SecretSchemaExtended(SecretSchema):
    version_data: SecretVersionSchema

    @staticmethod
    def resolve_version_data(obj, context):
        tags_per_version = {}
        for tag, ver in obj.tags.items():
            tags_per_version.setdefault(ver, []).append(tag)

        requested_version = getattr(obj, "_requested_version", "latest")
        if not is_valid_positive_int(requested_version):
            resolved = obj.tags.get(requested_version)
            if resolved is None:
                raise VersionNotFound("Specified tag wasn't found")
            requested_version = resolved

        if requested_version != "latest":
            version_obj = obj.versions.filter(version=requested_version).first()
            if not version_obj:
                raise VersionNotFound("Specified version wasn't found")
        else:
            version_obj = obj.versions.order_by("-version").first()

        version_obj.tags = tags_per_version.get(version_obj.version, [])
        # Populated when GET ?reveal=true (see TreeManager.get_extended).
        version_obj.data = getattr(obj, "_decrypted_plaintext", None)
        return version_obj


class ResolverSchema(BaseNodeSchema):
    node_type: Literal["resolver"]
    created_at: datetime = Field(..., description="Creation timestamp")
    configuration: str | None = Field(None, json_schema_extra={"format": "textarea"})
    token1: str | None = None
    token1_last_used: datetime | None = None
    token2: str | None = None
    token2_last_used: datetime | None = None

    @staticmethod
    def resolve_token1(obj, context):
        reveal_token = obj.get("_reveal_token1") if isinstance(obj, dict) else getattr(obj, "_reveal_token1", None)
        if isinstance(obj, dict):
            token = None
        else:
            mgr = ResolverTokenManager.from_resolver(obj, 1)
            token = getattr(obj, "_reveal_plaintext_token1", None) or (mgr.plaintext if mgr is not None else None)
        return mask_resolver_token(token) if not reveal_token else token

    @staticmethod
    def resolve_token2(obj, context):
        reveal_token = obj.get("_reveal_token2") if isinstance(obj, dict) else getattr(obj, "_reveal_token2", None)
        if isinstance(obj, dict):
            token = None
        else:
            mgr = ResolverTokenManager.from_resolver(obj, 2)
            token = getattr(obj, "_reveal_plaintext_token2", None) or (mgr.plaintext if mgr is not None else None)
        return mask_resolver_token(token) if not reveal_token else token


class ResolverTokenRotationResponseSchema(Schema):
    token_number: int = Field(..., description="Token number to rotate")
    token: str = Field(..., description="New token value")


# Discriminated unions
AnyNodeSchema = Annotated[
    ConfigSchema | TemplateSchema | SecretSchema | ResolverSchema | FolderSchema, Field(discriminator="node_type")
]
AnyExtendedNodeSchema = Annotated[
    ConfigSchemaExtended | TemplateSchemaExtended | SecretSchemaExtended | ResolverSchema | FolderSchema,
    Field(discriminator="node_type"),
]
ExtendedConfigSchema = Annotated[
    ConfigSchemaExtended | TemplateSchemaExtended | SecretSchemaExtended, Field(discriminator="node_type")
]
AnyConfigSchema = Annotated[ConfigSchema | TemplateSchema | SecretSchema, Field(discriminator="node_type")]


class VersionSummarySchema(Schema):
    """One version row in a version history list (metadata only; no content)."""

    version: int = Field(..., description="Immutable version number", examples=[3])
    tags: list[str] = Field(
        ...,
        description="Tag names pointing at this version (e.g. latest, stable, custom)",
        examples=[["latest", "stable"]],
    )
    updater: str = Field(..., description="Identity that created this version")
    updated_at: datetime = Field(..., description="UTC timestamp when this version was created")
    deleted_at: datetime | None = Field(
        None,
        description="Set when this version was soft-deleted; content is cleared",
    )


class VersionHistoryResponseSchema(Schema):
    """All versions of a config, template, or secret (newest first)."""

    item: AnyConfigSchema = Field(..., description="Tree item metadata and tag map")
    versions: list[VersionSummarySchema] = Field(
        ...,
        description="Version history entries without document content",
    )
    versions_count: int = Field(
        ...,
        description="Total number of versions for this item (before pagination)",
    )


class NavigationSchema(Schema):
    item: TreeNavigationNodeSchema | None
    children: list[TreeNavigationNodeSchema]
    children_count: int = Field(
        ...,
        description="Total number of child nodes (before pagination)",
    )
    breadcrumbs: list[str]
    is_leaf: bool


class DiffSideSchema(Schema):
    """One side of a tree item diff (path, resolved version, optional content)."""

    path: str = Field(..., description="Tree path for this side")
    node_type: str = Field(..., description="Item type discriminator")
    requested: str = Field(
        ...,
        description="Version or tag as requested (?from= / ?to=)",
        examples=["latest", "5", "stable"],
    )
    version: int = Field(..., description="Resolved immutable version number")
    data: str | None = Field(
        None,
        description="Version body (config/template text or decrypted secret); omitted when decryption is required",
    )


class DiffResponseSchema(Schema):
    """Compare two versions or two paths; client renders the diff from both sides."""

    path: str = Field(..., description="Primary path from the URL")
    to_path: str | None = Field(
        None,
        description="Second path when ?to_path= is used for cross-item diff",
    )
    from_side: DiffSideSchema
    to_side: DiffSideSchema
    identical: bool | None = Field(
        None,
        description="True when both sides have comparable plaintext and content matches",
    )
    decryption_required: bool = Field(
        False,
        description="True for secret diff without ?reveal=true; content is not returned",
    )


class ResolvedItemSchema(Schema):
    """One resolved output document.

    Mirrors the design's resolve response item: `url` is the short-lived
    signed download URL for this artifact; the resolved bytes are NEVER
    returned inline.
    """

    name: str
    version: int
    format: str
    url: str | None = None
    checksum: str | None = None
    trace: dict[str, Any] = Field(default_factory=dict)


class EffectiveResolverHooksSchema(Schema):
    """Hook commands from the effective resolver configuration."""

    validate: str | None = None
    validate_all: str | None = None
    post_resolve: str | None = None
    post_resolve_all: str | None = None


class EffectiveResolverSchema(Schema):
    """Effective resolver configuration for a resolver-authenticated resolve call."""

    cast: str | None = None
    parameters: dict[str, Any] | None = None
    hooks: EffectiveResolverHooksSchema | None = None


class ResolveResponseSchema(Schema):
    items: list[ResolvedItemSchema]
    length: int
    trace_only: bool | None = None
    root: dict[str, Any] | None = None
    resolver: EffectiveResolverSchema | None = None

    @staticmethod
    def resolve_length(obj, context):
        items = obj.get("items") if isinstance(obj, dict) else getattr(obj, "items", [])
        return len(items or [])


class ResolvedParameterSchema(Schema):
    """One parameter row in the `/~resolve-parameters/` debug response."""

    type: str
    description: str = ""
    selector: str | None = None
    secret_reference: str | None = None
    declared_default: Any | None = None
    raw_value: Any | None = None
    effective_value: Any | None = None
    transformers_applied: list[str] = Field(default_factory=list)
    caller_supplied: bool | None = None


class ResolveParametersResponseSchema(Schema):
    path: str
    version: int
    requested_version: str
    parameters: dict[str, ResolvedParameterSchema] = Field(default_factory=dict)


class CastFormatSchema(Schema):
    """One supported cast output format and its option JSON Schema."""

    format: str = Field(..., description="Cast format identifier (yaml, json, env, …)")
    options_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema for ``cast_option_*`` query parameters",
    )


class CastFormatsListSchema(Schema):
    formats: list[CastFormatSchema]


class LockSchema(Schema):
    """Active subtree lock at a tree path."""

    path: str = Field(..., description="Locked path (covers this path and descendants)")
    reason: str = Field(..., description="Freeze rationale")
    expires_at: datetime | None = Field(
        None,
        description="UTC expiry; null means until explicitly removed",
    )
    locked_by: str = Field(
        "",
        description="Identity that created the lock",
    )
    created_at: datetime
    updated_at: datetime


class LocksListSchema(Schema):
    locks: list[LockSchema]
    count: int


# Global Permissions
class GlobalPermissionRuleSchema(Schema):
    id: uuid.UUID
    position: float
    rule: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GlobalPermissionRulesListSchema(Schema):
    rules: list[GlobalPermissionRuleSchema]
    count: int
