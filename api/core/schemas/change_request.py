from datetime import datetime
from typing import Literal

from ninja import Schema
from pydantic import ConfigDict, Field, field_validator, model_validator

_CR_STATUS = Literal["open", "rejected", "withdrawn", "applied"]
_VERSIONED_NODE_TYPE = Literal["config", "template", "secret"]

_TITLE_MAX = 200
_DESCRIPTION_MAX = 4096
_REASON_MAX = 4096
_COMMENT_BODY_MAX = 8192
_IDENTITY_MAX = 512
_LIST_LIMIT_MAX = 500


class _ChangeRequestInputSchema(Schema):
    """Reject unknown JSON fields on change-request write payloads."""

    model_config = ConfigDict(extra="forbid")


class ChangeRequestAnchorSchema(_ChangeRequestInputSchema):
    start_line: int = Field(..., ge=1, description="1-based start line in CR content")
    end_line: int | None = Field(
        None,
        ge=1,
        description="1-based end line (inclusive); defaults to start_line when omitted",
    )

    @model_validator(mode="after")
    def end_line_not_before_start(self) -> "ChangeRequestAnchorSchema":
        if self.end_line is not None and self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class ChangeRequestApprovalEventSchema(Schema):
    approver: str = Field(..., max_length=_IDENTITY_MAX)
    created_at: datetime


class ChangeRequestReferrerSchema(Schema):
    path: str = Field(..., min_length=1)
    node_type: _VERSIONED_NODE_TYPE
    number: int = Field(..., ge=1)


class ChangeRequestSchema(Schema):
    path: str = Field(..., min_length=1)
    node_type: _VERSIONED_NODE_TYPE
    number: int = Field(..., ge=1)
    status: _CR_STATUS
    base_version: int = Field(..., ge=1)
    title: str = Field(..., max_length=_TITLE_MAX)
    description: str = Field(..., max_length=_DESCRIPTION_MAX)
    created_by: str = Field(..., max_length=_IDENTITY_MAX)
    created_at: datetime
    updated_at: datetime
    applied_version: int | None = Field(None, ge=1)
    applied_by: str | None = Field(None, max_length=_IDENTITY_MAX)
    applied_at: datetime | None = None
    rejected_reason: str = Field("", max_length=_REASON_MAX)
    rejected_by: str | None = Field(None, max_length=_IDENTITY_MAX)
    rejected_at: datetime | None = None
    approvers: list[str]
    approval_events: list[ChangeRequestApprovalEventSchema] = Field(
        default_factory=list,
        description="Approvals in chronological order",
    )
    base_superseded: bool
    latest_version: int = Field(..., ge=0)
    approval_count: int = Field(..., ge=0)
    required_approvals: int = Field(..., ge=0)
    can_apply: bool
    can_approve: bool
    can_unapprove: bool
    projected_version_on_apply: int = Field(..., ge=1)
    has_cr_references: bool
    referenced_by: list[ChangeRequestReferrerSchema] = Field(
        default_factory=list,
        description="Open change requests whose _ocmo metadata references this CR",
    )
    depends_on: list[ChangeRequestReferrerSchema] = Field(
        default_factory=list,
        description="Other change requests referenced from this CR's _ocmo metadata (@~N)",
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Validation and policy problems that may block apply or safe use",
    )
    content: str | None = None

    @field_validator("approvers")
    @classmethod
    def approver_identities_bounded(cls, value: list[str]) -> list[str]:
        for entry in value:
            if len(entry) > _IDENTITY_MAX:
                raise ValueError(f"approver identity exceeds {_IDENTITY_MAX} characters")
        return value


class ChangeRequestMetadataPatchSchema(_ChangeRequestInputSchema):
    title: str | None = Field(None, min_length=1, max_length=_TITLE_MAX)
    description: str | None = Field(None, max_length=_DESCRIPTION_MAX)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be empty")
        return stripped

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ChangeRequestMetadataPatchSchema":
        if self.title is None and self.description is None:
            raise ValueError("At least one of title or description must be provided")
        return self


class ChangeRequestListSchema(Schema):
    items: list[ChangeRequestSchema]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=_LIST_LIMIT_MAX)
    offset: int = Field(..., ge=0)


class ChangeRequestListQuerySchema(_ChangeRequestInputSchema):
    """Query parameters for listing change requests on one item path."""

    status: _CR_STATUS | None = None
    created_by: str | None = Field(None, min_length=1, max_length=_IDENTITY_MAX)
    limit: int = Field(100, ge=1, le=_LIST_LIMIT_MAX)
    offset: int = Field(0, ge=0)


class ChangeRequestCreateQuerySchema(_ChangeRequestInputSchema):
    title: str = Field(..., min_length=1, max_length=_TITLE_MAX)
    description: str = Field("", max_length=_DESCRIPTION_MAX)
    base_version: str | None = Field(
        None,
        min_length=1,
        max_length=64,
        description="Version or tag to use as base (default latest)",
    )

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be empty")
        return stripped

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return value.strip()

    @field_validator("base_version")
    @classmethod
    def normalize_base_version(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ChangeRequestRejectSchema(_ChangeRequestInputSchema):
    reason: str = Field("", max_length=_REASON_MAX)


class ChangeRequestCommentSchema(Schema):
    id: int = Field(..., ge=1)
    author: str = Field(..., max_length=_IDENTITY_MAX)
    body: str = Field(..., min_length=1, max_length=_COMMENT_BODY_MAX)
    anchor: ChangeRequestAnchorSchema | None = None
    created_at: datetime


class ChangeRequestCommentCreateSchema(_ChangeRequestInputSchema):
    body: str = Field(..., min_length=1, max_length=_COMMENT_BODY_MAX)
    anchor: ChangeRequestAnchorSchema | None = None

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("body must not be empty")
        return stripped


class ChangeRequestCommentUpdateSchema(_ChangeRequestInputSchema):
    body: str = Field(..., min_length=1, max_length=_COMMENT_BODY_MAX)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("body must not be empty")
        return stripped


class ChangeRequestCommentListSchema(Schema):
    items: list[ChangeRequestCommentSchema]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=_LIST_LIMIT_MAX)
    offset: int = Field(..., ge=0)
