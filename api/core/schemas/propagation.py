from typing import Literal

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..shortcuts import parse_ref, validate_path_characters
from .generic import UriReference


class ConfigPropagationSchema(BaseModel):
    """``_ocmo.propagation`` block: push config changes to downstream targets."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        False,
        description="When false, propagation rules are stored but do not fire.",
    )
    trigger: Literal["tag", "manual"] = Field(
        ...,
        description=(
            "``tag``: fire when a matching tag is set on this config. ``manual``: fire via ``POST /~propagate/{path}``."
        ),
    )
    tag: str | None = Field(
        None,
        description=("Glob pattern matched against the tag name that was set. Required when ``trigger`` is ``tag``."),
        examples=["stable", "release-*"],
    )
    mode: Literal["data", "whole"] = Field(
        "data",
        description=(
            "``data`` (default): merge source data only; target ``_ocmo`` is unchanged. "
            "``whole``: merge source data and ``_ocmo``; target keeps its own ``propagation`` block."
        ),
    )
    targets: list[UriReference] = Field(
        ...,
        min_length=1,
        description=(
            "Config paths to update (optional ``@version`` suffix per target). Glob patterns are not supported."
        ),
        examples=[["proj/qa/app/config", "proj/perf/app/config@stable"]],
    )
    exclude: list[str] = Field(
        default_factory=list,
        description=("Dot-separated field paths into the config data body to omit from propagation (not JSONPath)."),
        examples=[["logging.log_level", "some.dev.specific.conf"]],
    )

    @field_validator("targets")
    @classmethod
    def validate_targets(cls, v: list[str]) -> list[str]:
        limit = settings.OCMO_MAX_PROPAGATION_TARGETS
        if len(v) > limit:
            raise ValueError(f"_ocmo.propagation.targets cannot list more than {limit} config references")
        normalized: list[str] = []
        for ref in v:
            ref = ref.strip()
            path, _version = parse_ref(ref)
            path = path.strip("/")
            try:
                validate_path_characters(path)
            except DjangoValidationError as exc:
                raise ValueError(str(exc)) from exc
            normalized.append(ref)
        return normalized

    @field_validator("exclude")
    @classmethod
    def validate_exclude_paths(cls, v: list[str]) -> list[str]:
        for path in v:
            if not path or path.startswith("."):
                raise ValueError(
                    f"Invalid exclude path {path!r}: use dot-separated field paths "
                    f"(e.g. logging.log_level), not JSONPath"
                )
            for part in path.split("."):
                if not part or not part.replace("_", "").replace("-", "").isalnum():
                    raise ValueError(f"Invalid exclude path segment in {path!r}")
        return v

    @model_validator(mode="after")
    def validate_tag_required(self):
        if self.trigger == "tag" and not self.tag:
            raise ValueError("_ocmo.propagation.tag is required when trigger is 'tag'")
        return self
