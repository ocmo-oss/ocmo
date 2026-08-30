from collections.abc import Callable

from ..tree_capabilities import is_builtin_namespace_config_path
from ._common import *


def collect_ocmo_reference_paths(
    metadata: ConfigOcmoMetadataSchema,
    *,
    base_folder: str,
) -> list[tuple[str, str, str]]:
    """Return ``(node_type, resolved_path, version_ref)`` pairs from ``_ocmo`` metadata."""
    if not metadata.model_dump(exclude_none=True):
        return []

    refs: list[tuple[str, str, str]] = []

    if metadata.extend:
        for ref in metadata.extend.configs:
            norm = normalize_extend_ref(ref)
            path, version = parse_ref(norm.path)
            refs.append(("config", resolve_relative_path(base_folder, path), version))

    if metadata.render:
        for ref in metadata.render.templates:
            path, version = parse_ref(ref)
            refs.append(("template", resolve_relative_path(base_folder, path), version))

    for decl in metadata.parameters.values():
        if decl.type != "secret":
            continue
        ref = decl.value.strip()
        if ":" in ref:
            ref, _field_path = ref.split(":", 1)
        path, version = parse_ref(ref)
        refs.append(("secret", resolve_relative_path(base_folder, path), version))

    if metadata.validation:
        path, version = parse_ref(metadata.validation.schema_path)
        refs.append(("config", resolve_relative_path(base_folder, path), version))

    return refs


def _reference_strings_from_metadata(metadata: ConfigOcmoMetadataSchema) -> list[str]:
    """Return raw reference strings that may contain ``{!param}`` placeholders."""
    refs: list[str] = []
    if metadata.extend:
        for ref in metadata.extend.configs:
            norm = normalize_extend_ref(ref)
            refs.append(norm.path)
    if metadata.render:
        refs.extend(metadata.render.templates)
    if metadata.validation is not None:
        refs.append(metadata.validation.schema_path)
    for decl in metadata.parameters.values():
        if decl.type == "secret":
            value = decl.value.strip()
            if ":" in value:
                value = value.split(":", 1)[0]
            refs.append(value)
    return refs


def _assert_no_unresolved_reference_placeholders(metadata: ConfigOcmoMetadataSchema) -> None:
    from ..resolve_parameters import PLACEHOLDER_RE

    for ref in _reference_strings_from_metadata(metadata):
        if PLACEHOLDER_RE.search(ref):
            raise ValidationError(
                f"Cannot validate _ocmo reference {ref!r}: unresolved parameter placeholder(s) remain "
                "after substituting declared defaults"
            )


class TreeConfigOpsMixin:
    def _metadata_for_reference_validation(
        self,
        metadata: ConfigOcmoMetadataSchema,
        body: Any,
        *,
        config_path: str | None = None,
    ) -> ConfigOcmoMetadataSchema:
        """Substitute parameter defaults into reference-bearing ``_ocmo`` fields for save checks."""
        from ..resolve_parameters import ParameterError, ResolveParametersManager

        if not metadata.model_dump(exclude_none=True):
            return metadata

        effective_path = config_path if config_path is not None else self.path
        metadata = metadata.model_copy(deep=True)
        name = effective_path.strip("/").split("/")[-1]
        config_stub = Config(namespace=self.namespace, path=effective_path, name=name)
        version_number = 1
        if self.item is not None and getattr(self.item, "tags", None):
            version_number = self.item.tags.get("latest", 1)

        params_mgr = ResolveParametersManager(
            self.namespace,
            config_stub,
            base_folder="/".join(effective_path.split("/")[:-1]),
            version_tag="latest",
            version_number=version_number,
            dynamic_params={},
            auth=self.auth,
            no_creds=True,
        )
        try:
            params_mgr.evaluate(body, metadata)
            metadata = params_mgr._substitute_metadata(metadata)
        except ParameterError as exc:
            raise ValidationError(str(exc)) from exc

        _assert_no_unresolved_reference_placeholders(metadata)
        return metadata

    def _validate_config_ocmo_references(
        self,
        metadata: ConfigOcmoMetadataSchema,
        *,
        config_path: str | None = None,
        resolve_db_path: Callable[[str], str] | None = None,
    ) -> None:
        """Ensure extend/render/secret paths referenced in ``_ocmo`` exist."""
        if not metadata.model_dump(exclude_none=True):
            return

        effective_path = config_path if config_path is not None else self.path
        base_folder = "/".join(effective_path.split("/")[:-1])

        def _db_path(resolved: str) -> str:
            if resolve_db_path is not None:
                return resolve_db_path(resolved)
            return resolved

        def _require_version(item, version: str) -> None:
            try:
                self.resolve_version(item, version)
            except VersionNotFound as exc:
                raise ValidationError(str(exc)) from exc

        if metadata.extend:
            for ref in metadata.extend.configs:
                norm = normalize_extend_ref(ref)
                path, version = parse_ref(norm.path)
                resolved = resolve_relative_path(base_folder, path)
                if resolved == effective_path:
                    raise ValidationError(
                        f"Config {effective_path!r} cannot reference itself in _ocmo.extend (reference {norm.path!r})"
                    )
                if not self._capabilities_for(resolved).is_extend_target:
                    raise CapabilityDenied(f"Config '{normalize_tree_path(resolved)}' cannot be used in extend")
                try:
                    item = type(self)(self.namespace, _db_path(resolved), auth=None).get_or_raise(["config"])
                except (TreeItem.DoesNotExist, NotFound):
                    raise ValidationError(f"Config {resolved!r} not found")
                _require_version(item, version)
                del item

        if metadata.render:
            for ref in metadata.render.templates:
                path, version = parse_ref(ref)
                resolved = resolve_relative_path(base_folder, path)
                try:
                    item = type(self)(self.namespace, _db_path(resolved), auth=None).get_or_raise(["template"])
                except (TreeItem.DoesNotExist, NotFound):
                    raise ValidationError(f"Template {resolved!r} not found")
                _require_version(item, version)
                del item

        for decl in metadata.parameters.values():
            if decl.type != "secret":
                continue
            ref = decl.value.strip()
            if ":" in ref:
                ref, _field_path = ref.split(":", 1)
            path, version = parse_ref(ref)
            resolved = resolve_relative_path(base_folder, path)
            if not self._capabilities_for(
                resolved,
                referencing_config_path=effective_path,
            ).is_available_for_param:
                raise CapabilityDenied(
                    f"Secret '{normalize_tree_path(resolved)}' cannot be referenced from config '{effective_path}'"
                )
            try:
                item = type(self)(self.namespace, _db_path(resolved), auth=None).get_or_raise(["secret"])
            except (TreeItem.DoesNotExist, NotFound):
                raise ValidationError(f"Secret {resolved!r} not found")
            _require_version(item, version)
            del item

        if metadata.validation:
            ref = metadata.validation.schema_path
            path, version = parse_ref(ref)
            resolved = resolve_relative_path(base_folder, path)
            db_path = _db_path(resolved)
            try:
                item = type(self)(self.namespace, db_path, auth=None).get_or_raise(["config"])
            except (TreeItem.DoesNotExist, NotFound):
                raise ValidationError(f"Schema config {resolved!r} not found")
            _require_version(item, version)
            schema_mgr = type(self)(self.namespace, db_path, auth=None)
            schema_metadata = schema_mgr.get_config_ocmo_metadata(version)
            if not schema_metadata.is_json_schema:
                raise ValidationError(
                    f"Config {resolved!r} is not marked as a JSON Schema (_ocmo.is_json_schema must be true)"
                )
            del item

    def _validate_config_on_save(self, data_yaml: str, *, validate_references: bool = True) -> ConfigDocumentParts:
        validator = ConfigValidationManager(config_path=self.path, data_yaml=data_yaml)

        validator.parse()
        validator.validate_document_structure()

        if validate_references:
            ref_metadata = self._metadata_for_reference_validation(validator.metadata, validator.parts.body)
            self._validate_config_ocmo_references(ref_metadata)

            schema_ref = ConfigValidationManager.resolve_schema_ref_for_path(self.path, ref_metadata)
            if schema_ref is not None:
                schema_path, version = schema_ref
                schema_mgr = type(self)(self.namespace, schema_path, auth=None)
                schema_metadata, schema_body = schema_mgr.load_config_version_document(version)
                schema_parts = ConfigDocumentParts(metadata=schema_metadata, body=schema_body)
                validator.validate_against_schema(schema_parts)

        if normalize_tree_path(self.path) == "_permissions":
            validator.validate_permissions()

        return validator.parts

    def load_config_version_document(self, version: str = "latest") -> tuple[ConfigOcmoMetadataSchema, Any]:
        """Load config *version*; return validated ``_ocmo`` metadata and data body."""
        item = self.get_or_raise(["config"])
        version_obj = self.resolve_version(item, version)
        return ConfigValidationManager.parse_config_yaml_document(version_obj.data)

    def get_config_ocmo_metadata(self, version: str = "latest") -> ConfigOcmoMetadataSchema:
        """Return validated ``_ocmo`` metadata for a config at *version*."""
        metadata, _ = self.load_config_version_document(version)
        return metadata

    @require_permissions(
        PermCheck(
            action=lambda self: "namespace:read" if is_builtin_namespace_config_path(self.path) else None,
            resource=lambda self: self.namespace.name,
        ),
        PermCheck(
            action=lambda self: "config:read" if not is_builtin_namespace_config_path(self.path) else None,
            resource=lambda self: self.path,
        ),
    )
    def get_config_data_json_schema(self, version: str = "latest") -> dict[str, Any]:
        """Return the JSON Schema document that validates this config's data body."""
        self.get_or_raise(["config"])
        metadata, _ = self.load_config_version_document(version)
        schema_ref = ConfigValidationManager.resolve_schema_ref_for_path(self.path, metadata)
        if schema_ref is None:
            raise NotFound(f"No JSON Schema defined for config {self.path!r}")
        schema_path, schema_version = schema_ref
        schema_mgr = type(self)(self.namespace, schema_path, auth=None)
        try:
            schema_metadata, schema_body = schema_mgr.load_config_version_document(schema_version)
        except (TreeItem.DoesNotExist, VersionNotFound) as exc:
            raise NotFound(f"Schema config {schema_path!r} not found for config {self.path!r}") from exc
        if not schema_metadata.is_json_schema:
            raise NotFound(f"Config {schema_path!r} is not marked as a JSON Schema (_ocmo.is_json_schema must be true)")
        if not isinstance(schema_body, dict):
            raise NotFound(f"Schema config {schema_path!r} body must be a mapping")
        if schema_path == "_permissions.schema":
            from ...utils.permissions_schema_document import apply_permissions_schema_actions

            return apply_permissions_schema_actions(schema_body)
        return schema_body

    def list_configs_under_folder(self, ignore_configs_with_missing_tags: bool, version: str) -> list[Config]:
        """Return all Config items whose path sits under this folder path, ordered."""
        if self.item.node_type == "folder":
            configs: list[Config] = []
            for cfg in Config.objects.filter(namespace=self.namespace, path__startswith=f"{self.path}/").order_by(
                "path"
            ):
                caps = compute_tree_capabilities(self.namespace, cfg.path, self.auth)
                if not caps.is_folder_resolvable:
                    continue
                if ignore_configs_with_missing_tags:
                    try:
                        self.resolve_version(cfg, version)
                    except VersionNotFound:
                        continue
                configs.append(cfg)
            return configs
        else:
            return []
