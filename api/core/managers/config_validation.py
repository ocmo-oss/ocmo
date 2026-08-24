"""Config document parsing and JSON Schema validation on create/update."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from ..schemas.requests import ConfigOcmoMetadataSchema
from ..shortcuts import parse_ref, resolve_relative_path, safe_yaml_load
from ..utils.permissions_compiler import PermissionsCompiler
from ..validation_errors import format_pydantic_validation_error_with_prefix
from .tree_capabilities import is_builtin_namespace_config_path

_PLACEHOLDER_RE = re.compile(r"\{!([a-zA-Z_][a-zA-Z0-9_]*)\}")


@dataclass(frozen=True)
class ConfigDocumentParts:
    metadata: ConfigOcmoMetadataSchema
    body: Any


class ConfigValidationManager:
    """Parse and validate config documents on save (no DB access)."""

    @staticmethod
    def parse_config_yaml_document(
        data: str | dict[str, Any],
    ) -> tuple[ConfigOcmoMetadataSchema, Any]:
        """Parse config YAML and return validated ``_ocmo`` metadata plus the data body.

        When the YAML root is a mapping, ``_ocmo`` (if present) is validated and
        removed from the returned body. For any other root type (scalar, sequence,
        null, etc.) the body is the parsed value as-is and metadata is empty.
        """
        if isinstance(data, str):
            try:
                parsed = safe_yaml_load(data)
            except Exception as exc:
                raise ValidationError("Payload is not valid YAML") from exc
        else:
            parsed = data

        if not isinstance(parsed, dict):
            return ConfigOcmoMetadataSchema.model_validate({}), parsed

        parsed = dict(parsed)
        meta_key = settings.OCMO_CONFIG_METADATA_KEY
        ocmo_block = parsed.pop(meta_key, {}) or {}
        try:
            metadata = ConfigOcmoMetadataSchema.model_validate(ocmo_block)
        except PydanticValidationError as exc:
            raise ValidationError(format_pydantic_validation_error_with_prefix(exc, prefix=meta_key)) from exc
        except Exception as exc:
            raise ValidationError(f"Invalid {meta_key} metadata: {exc}") from exc
        return metadata, parsed

    def __init__(self, *, config_path: str, data_yaml: str) -> None:
        self.config_path = config_path.strip("/")
        self.data_yaml = data_yaml
        self._parts: ConfigDocumentParts | None = None

    def _ensure_parsed(self) -> ConfigDocumentParts:
        if self._parts is None:
            self.parse()
        return self._parts  # type: ignore[return-value]

    @property
    def parts(self) -> ConfigDocumentParts:
        return self._ensure_parsed()

    @property
    def metadata(self) -> ConfigOcmoMetadataSchema:
        return self.parts.metadata

    @property
    def body(self) -> Any:
        return self.parts.body

    def parse(self) -> ConfigDocumentParts:
        metadata, body = self.parse_config_yaml_document(self.data_yaml)
        self._parts = ConfigDocumentParts(metadata=metadata, body=body)
        return self._parts

    def _validate_json_schema_syntax(self, data_dict: dict[str, Any]) -> None:
        """Raise ValidationError when *data_dict* is not a valid JSON Schema document."""
        try:
            Draft202012Validator.check_schema(data_dict)
        except SchemaError as exc:
            raise ValidationError(f"Invalid JSON Schema: {exc.message}") from exc

    def _collect_parameter_references(self, value: Any) -> set[str]:
        """Return parameter names referenced via ``{!name}`` placeholders in ``value``."""
        refs: set[str] = set()
        if isinstance(value, str):
            for match in _PLACEHOLDER_RE.finditer(value):
                name = match.group(1)
                if name != "omit":
                    refs.add(name)
        elif isinstance(value, Mapping):
            for item in value.values():
                refs |= self._collect_parameter_references(item)
        elif isinstance(value, list):
            for item in value:
                refs |= self._collect_parameter_references(item)
        return refs

    def _validate_declared_parameters_used(
        self,
        metadata: ConfigOcmoMetadataSchema,
        body: Any,
    ) -> None:
        """Reject declared parameters that do not appear anywhere in the config body."""
        if not metadata.parameters:
            return
        referenced = self._collect_parameter_references(body)
        referenced |= self._collect_parameter_references(metadata.model_dump(exclude_none=True))
        unused = set(metadata.parameters) - referenced
        unused -= {name for name, decl in metadata.parameters.items() if decl.type == "secret"}
        if unused:
            names = ", ".join(sorted(unused))
            raise ValueError(f"Declared parameter(s) not referenced in config data: {names}")

    def validate_document_structure(self) -> None:
        parts = self._ensure_parsed()
        try:
            self._validate_declared_parameters_used(parts.metadata, parts.body)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        if is_builtin_namespace_config_path(self.config_path):
            if parts.metadata.validation is not None:
                raise ValidationError("Built-in namespace configs cannot declare _ocmo.validation")
            if parts.metadata.propagation is not None:
                raise ValidationError("Built-in namespace configs cannot declare _ocmo.propagation")

        if parts.metadata.propagation is not None:
            normalized = self.config_path.strip("/")
            for target in parts.metadata.propagation.targets:
                target_path, _ = parse_ref(target.strip())
                if target_path.strip("/") == normalized:
                    raise ValidationError("Source config path cannot appear in _ocmo.propagation.targets")

        if parts.metadata.is_json_schema:
            if not isinstance(parts.body, dict):
                raise ValidationError("JSON Schema config body must be a mapping")
            self._validate_json_schema_syntax(parts.body)

    def resolve_schema_ref(self) -> tuple[str, str] | None:
        parts = self._ensure_parsed()
        return self.resolve_schema_ref_for_path(self.config_path, parts.metadata)

    @staticmethod
    def resolve_schema_ref_for_path(
        config_path: str,
        metadata: ConfigOcmoMetadataSchema,
    ) -> tuple[str, str] | None:
        """Return (schema_config_path, version) for *config_path* data validation."""
        base_folder = "/".join(config_path.split("/")[:-1])
        normalized = config_path.strip("/")
        if is_builtin_namespace_config_path(normalized):
            return f"{normalized}.schema", "latest"
        if metadata.validation is None:
            return None
        path, version = parse_ref(metadata.validation.schema_path)
        resolved = resolve_relative_path(base_folder, path)
        return resolved, version

    def validate_against_schema(self, schema_parts: ConfigDocumentParts) -> None:
        parts = self._ensure_parsed()
        schema_ref = self.resolve_schema_ref()
        schema_path = schema_ref[0] if schema_ref else self.config_path

        if not schema_parts.metadata.is_json_schema:
            raise ValidationError(
                f"Config {schema_path!r} is not marked as a JSON Schema (_ocmo.is_json_schema must be true)"
            )

        if not isinstance(schema_parts.body, dict):
            raise ValidationError(f"Schema config {schema_path!r} body must be a mapping")

        try:
            Draft202012Validator(schema_parts.body).validate(parts.body)
        except JsonSchemaValidationError as exc:
            instance_path = ".".join(str(part) for part in exc.absolute_path) or "(root)"
            raise ValidationError(
                f"Config data failed JSON Schema validation from {schema_path!r}: {instance_path}: {exc.message}"
            ) from exc

    def validate_permissions(self) -> None:
        """Ensure _permissions resource globs compile (schema cannot run glob_to_regex)."""
        parts = self._ensure_parsed()
        if not isinstance(parts.body, dict):
            return
        for policy in parts.body.get("policies", []):
            if not isinstance(policy, dict):
                continue
            for glob in policy.get("resources", []):
                if not isinstance(glob, str):
                    continue
                try:
                    regex_str, _ = PermissionsCompiler.glob_to_regex(glob)
                    re.compile(regex_str)
                except ValueError as exc:
                    raise ValidationError(str(exc)) from exc
                except re.error as exc:
                    raise ValidationError(f"Invalid resource glob {glob!r}: {exc}") from exc
