"""Parameter evaluation and placeholder substitution for config resolving.

Implements the parameters step from ``docs/resolving-parameters-feature.md``:
evaluate declared parameters (projected, dynamic, secret), apply transformers,
and substitute ``{!name}`` / ``{!omit}`` placeholders into the config body and
selected ``_ocmo`` metadata fields.

Projected selectors include ``.Name``, ``.Path``, ``.Path[N]``, ``.Data.*``,
``.Version.tag``, and ``.Version.number``.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.parse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import Any

from ..constants.resolve import OMIT
from ..decorators import PermCheck, audit, require_permissions, webhook
from ..exceptions import CapabilityDenied, ParameterError, SecretParameterError
from ..models import Config
from ..schemas import ConfigExtendRefSchema, ConfigOcmoMetadataSchema
from ..shortcuts import json_path, parse_ref, resolve_relative_path, safe_yaml_load, to_plain
from .auth import AuthManager
from .secret import SecretManager
from .tree import TreeManager

PLACEHOLDER_RE = re.compile(r"\{!([a-zA-Z_][a-zA-Z0-9_]*)\}")
PLACEHOLDER_ONLY_RE = re.compile(
    r"^\s*\{!([a-zA-Z_][a-zA-Z0-9_]*)\}\s*$",
)

SECRET_DUMMY_VALUE = "<secret-value-placeholder>"


@dataclass(frozen=True, slots=True)
class MultilineValue:
    """Marker for parameter values that keep newlines on full-value substitution."""

    value: str

    def __str__(self) -> str:
        return self.value


def _coerce_param_string(value: Any) -> str:
    if isinstance(value, MultilineValue):
        return value.value
    return str(value)


def _single_line_string(value: Any) -> str:
    return _coerce_param_string(value).replace("\n", " ").replace("\r", " ")


def _t_lower(v):
    return str(v).lower()


def _t_upper(v):
    return str(v).upper()


def _t_slug(v):
    s = re.sub(r"[^A-Za-z0-9]+", "-", str(v))
    return re.sub(r"-{2,}", "-", s).strip("-")


def _t_snake(v):
    s = re.sub(r"[^A-Za-z0-9]+", "_", str(v))
    return re.sub(r"_{2,}", "_", s).strip("_")


def _t_trim(v):
    return str(v).strip()


def _t_escape_html(v):
    return html_escape(str(v), quote=True)


def _t_b64_encode(v):
    return base64.b64encode(str(v).encode("utf-8")).decode("ascii")


def _t_urlencode(v):
    return urllib.parse.quote(str(v), safe="")


def _t_int(v):
    return int(str(v).strip())


def _t_float(v):
    return float(str(v).strip())


def _t_bool(v):
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    raise ParameterError(f"Cannot cast {v!r} to bool")


def _t_null(v):
    if v is None:
        return None
    if isinstance(v, str) and not v.strip():
        return None
    return v


def _t_multiline(v):
    return MultilineValue(_coerce_param_string(v))


def _t_omit(v):
    if v is OMIT:
        return OMIT
    if v is None:
        return OMIT
    if isinstance(v, str) and not v.strip():
        return OMIT
    if isinstance(v, MultilineValue):
        return v
    return v


_TRANSFORMERS = {
    "lower": _t_lower,
    "upper": _t_upper,
    "slug": _t_slug,
    "snake": _t_snake,
    "trim": _t_trim,
    "escape_html": _t_escape_html,
    "b64_encode": _t_b64_encode,
    "urlencode": _t_urlencode,
    "int": _t_int,
    "float": _t_float,
    "bool": _t_bool,
    "null": _t_null,
    "multiline": _t_multiline,
    "omit": _t_omit,
}


def _apply_transformers(value: Any, transformers: Sequence[str]) -> Any:
    for name in transformers:
        fn = _TRANSFORMERS.get(name)
        if fn is None:
            raise ParameterError(f"Unknown transformer {name!r}")
        value = fn(value)
    return value


def _secret_document_value(parsed: Any, plaintext: str, *, allow_multiline: bool) -> Any:
    """Resolve a whole-secret reference (no ``:field`` suffix)."""
    if isinstance(parsed, Mapping) or isinstance(parsed, list):
        return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    if isinstance(parsed, str):
        # Plain multi-line PEM/text files are often folded to one line by YAML
        # parsers; keep the raw plaintext when multiline embedding is requested.
        if allow_multiline and "\n" in plaintext and "\n" not in parsed:
            return plaintext
        return parsed
    return plaintext


def _parameter_effective_display_value(transformed: Any, *, is_secret: bool) -> Any:
    if is_secret:
        return "***"
    if transformed is OMIT:
        return None
    if isinstance(transformed, MultilineValue):
        return transformed.value
    return transformed


class ResolveParametersManager:
    """Evaluate parameters and substitute placeholders for one Config."""

    def __init__(
        self,
        namespace,
        config: Config,
        *,
        base_folder: str,
        version_tag: str,
        version_number: int,
        dynamic_params: dict[str, Any] | None = None,
        auth: AuthManager | None = None,
        no_creds: bool = False,
    ):
        self.namespace = namespace
        self.auth = auth
        self.config = config
        self.base_folder = base_folder
        self.version_tag = version_tag
        self.version_number = version_number
        self.dynamic_params = dict(dynamic_params or {})
        self.no_creds = no_creds
        self.parameters_effective: dict[str, Any] = {}
        self.parameters_meta: dict[str, dict[str, Any]] = {}
        # Populated during evaluate(); each entry: {kind, path, ref, version}
        self.resolved_secrets: list[dict[str, Any]] = []

    def apply(self, body: Any, metadata: ConfigOcmoMetadataSchema) -> tuple[Any, ConfigOcmoMetadataSchema]:
        """Evaluate parameters, substitute body and metadata placeholders."""
        self.evaluate(body, metadata)
        body = self._substitute(body, self.parameters_effective)
        metadata = self._substitute_metadata(metadata)
        return body, metadata

    def evaluate(self, body: Any, metadata: ConfigOcmoMetadataSchema) -> None:
        """Populate ``parameters_effective`` and ``parameters_meta`` only."""
        path_segments = self.config.path.split("/")
        context = {
            "Name": self.config.name,
            "Path": self.config.path,
            "PathSegments": path_segments,
            "Data": to_plain(body),
            "Version": {
                "tag": self.version_tag,
                "number": self.version_number,
            },
        }

        declared = metadata.parameters or {}
        effective: dict[str, Any] = {}
        parameters_meta: dict[str, dict[str, Any]] = {}

        for name, decl in declared.items():
            raw_value: Any
            meta_entry: dict[str, Any] = {
                "type": decl.type,
                "description": decl.description,
                "transformers_applied": list(decl.transformers),
            }

            if decl.type == "projected":
                raw_value = self._eval_projected(decl.value, context)
                meta_entry["selector"] = decl.value
                meta_entry["raw_value"] = raw_value
                transformed = _apply_transformers(raw_value, decl.transformers)
            elif decl.type == "dynamic":
                if name in self.dynamic_params:
                    raw_value = self.dynamic_params[name]
                    meta_entry["caller_supplied"] = True
                else:
                    raw_value = decl.value
                    meta_entry["caller_supplied"] = False
                meta_entry["declared_default"] = decl.value
                transformed = _apply_transformers(raw_value, decl.transformers)
            elif decl.type == "secret":
                meta_entry["secret_reference"] = decl.value
                if self.no_creds:
                    meta_entry["no_creds"] = True
                    meta_entry["transformers_skipped"] = True
                    transformed = SECRET_DUMMY_VALUE
                else:
                    raw_value = self._resolve_secret_value(
                        decl.value,
                        allow_multiline=bool({"b64_encode", "multiline"} & set(decl.transformers)),
                    )
                    transformed = _apply_transformers(raw_value, decl.transformers)
            else:
                raise ParameterError(f"Unknown parameter type {decl.type!r}")

            effective[name] = transformed
            if decl.type == "secret" and self.no_creds:
                meta_entry["effective_value"] = SECRET_DUMMY_VALUE
            else:
                meta_entry["effective_value"] = _parameter_effective_display_value(
                    transformed,
                    is_secret=decl.type == "secret",
                )
            parameters_meta[name] = meta_entry

        self.parameters_effective = effective
        self.parameters_meta = parameters_meta

    def _substitute_metadata(self, metadata: ConfigOcmoMetadataSchema) -> ConfigOcmoMetadataSchema:
        """Substitute `{!param}` placeholders in extend / render / name fields."""

        params = self.parameters_effective

        def sub(value: Any) -> Any:
            result = self._substitute(value, params)
            return result if result is not OMIT else None

        if metadata.extend is not None:
            updated_configs: list[str | ConfigExtendRefSchema] = []
            for ref in metadata.extend.configs:
                if isinstance(ref, str):
                    updated_configs.append(sub(ref))
                else:
                    ref.path = sub(ref.path)
                    updated_configs.append(ref)
            metadata.extend.configs = updated_configs
        if metadata.render is not None:
            metadata.render.templates = [sub(t) for t in metadata.render.templates]
        if metadata.name is not None:
            metadata.name = sub(metadata.name)
        return metadata

    def _eval_projected(self, selector: str, context: dict[str, Any]) -> Any:
        if not selector or not selector.startswith("."):
            raise ParameterError(f"Projected parameter selector must start with '.': {selector!r}")
        if selector == ".Name":
            return context["Name"]
        if selector == ".Path":
            return context["Path"]
        m = re.match(r"^\.Path\[(-?\d+)\]$", selector)
        if m:
            segments = context["PathSegments"]
            idx = int(m.group(1))
            try:
                return segments[idx]
            except IndexError:
                raise ParameterError(f"Path index {idx} out of range for {context['Path']!r}")
        if selector == ".Version.tag":
            return context["Version"]["tag"]
        if selector == ".Version.number":
            return context["Version"]["number"]
        if selector.startswith(".Data"):
            try:
                return json_path(context["Data"], "." + selector[len(".Data") :].lstrip("."))
            except ValueError as exc:
                raise ParameterError(str(exc)) from exc
        raise ParameterError(f"Unsupported projected selector {selector!r}")

    def _secret_resolve_path(self, reference: str) -> str:
        ref = reference.strip()
        if ":" in ref:
            ref = ref.split(":", 1)[0]
        path, _ = parse_ref(ref)
        return resolve_relative_path(self.base_folder, path)

    @webhook(
        "secret.resolved",
        path=lambda self, result, bound: self.resolved_secrets[-1]["path"] if self.resolved_secrets else None,
        version=lambda self, result, bound: self.resolved_secrets[-1]["version"] if self.resolved_secrets else None,
        details=lambda self, result, bound: (
            {
                "config_path": self.config.path,
                "ref": self.resolved_secrets[-1]["ref"],
            }
            if self.resolved_secrets
            else None
        ),
        skip_when=lambda self, result, bound: self.auth is None or self.no_creds,
    )
    @require_permissions(
        PermCheck(
            "secret:resolve",
            resource=lambda self, reference: self._secret_resolve_path(reference),
        )
    )
    def _resolve_secret_value(self, reference: str, *, allow_multiline: bool = False) -> str:
        """Resolve ``<path>[@version][:field.subfield]`` against this namespace."""

        ref = reference.strip()
        field_path: str | None = None
        if ":" in ref:
            ref, field_path = ref.split(":", 1)
        path, version_ref = parse_ref(ref)
        resolved_path = resolve_relative_path(self.base_folder, path)
        sm = SecretManager(self.namespace, resolved_path, auth=self.auth)
        secret = sm.get_or_raise()

        tm = TreeManager.for_item(
            self.namespace,
            secret,
            auth=self.auth,
            referencing_config_path=self.config.path,
        )
        if not tm.is_available_for_param:
            raise CapabilityDenied(f"Secret '{resolved_path}' cannot be referenced from config '{self.config.path}'")

        version_number, plaintext = sm.resolve_plaintext_at_version(version_ref)

        # Track for cache descriptor and trace
        self.resolved_secrets.append(
            {
                "kind": "secret",
                "path": resolved_path,
                "ref": version_ref,
                "version": version_number,
            }
        )

        try:
            parsed = safe_yaml_load(plaintext)
        except Exception:
            parsed = plaintext

        if field_path:
            cursor: Any = parsed
            for part in field_path.split("."):
                if not isinstance(cursor, Mapping):
                    raise SecretParameterError(f"Secret {resolved_path}: cannot descend into {part!r} of non-mapping")
                if part not in cursor:
                    raise SecretParameterError(f"Secret {resolved_path}: field {field_path!r} not present")
                cursor = cursor[part]
            value = cursor
        else:
            value = _secret_document_value(parsed, plaintext, allow_multiline=allow_multiline)

        if not isinstance(value, str):
            value = json.dumps(value, separators=(",", ":"), ensure_ascii=False)

        if "\n" in value and not allow_multiline:
            raise SecretParameterError(
                f"Secret value for {reference!r} contains newlines; use the b64_encode transformer to embed safely"
            )
        return value

    @classmethod
    def _substitute_param_value(cls, value: Any, *, inline: bool) -> Any:
        if value is OMIT:
            return OMIT
        if isinstance(value, MultilineValue):
            return _single_line_string(value) if inline else value.value
        if value is None:
            return None
        if isinstance(value, str):
            return _single_line_string(value)
        return value

    @classmethod
    def _substitute(cls, value: Any, params: dict[str, Any]) -> Any:
        """Replace `{!name}` placeholders inside any string in ``value``."""

        if isinstance(value, Mapping):
            return {k: cls._substitute(v, params) for k, v in value.items()}
        if isinstance(value, list):
            return [cls._substitute(v, params) for v in value]
        if not isinstance(value, str):
            return value

        m = PLACEHOLDER_ONLY_RE.fullmatch(value)
        if m:
            name = m.group(1)
            if name == "omit":
                return OMIT
            if name in params:
                return cls._substitute_param_value(params[name], inline=False)
            return value

        def _replace(match: re.Match) -> str:
            name = match.group(1)
            if name == "omit":
                return ""
            if name in params:
                v = params[name]
                if v is OMIT:
                    return ""
                if v is None:
                    return ""
                if isinstance(v, MultilineValue) or isinstance(v, str):
                    return _single_line_string(v)
                return str(v)
            return match.group(0)

        return PLACEHOLDER_RE.sub(_replace, value)

    @audit(
        "config",
        object_id_attr=lambda self: self.config.path,
        resolve_type="direct",
        operation="Resolve",
    )
    @require_permissions(PermCheck("config:resolve", resource=lambda self: self.config.path))
    def resolve_debug(self) -> dict[str, Any]:
        """Return effective parameter metadata for a single Config (debug API)."""
        tm = TreeManager.for_item(self.namespace, self.config, auth=self.auth)
        if not tm.is_resolvable:
            raise CapabilityDenied(
                f"Config by path '{self.config.path}' can't be resolved without namespace level write permission"
            )
        if not tm.is_direct_resolve_target:
            raise CapabilityDenied(
                f"Config '{self.config.path}' is outside resolver scope and cannot be resolved directly"
            )

        version_obj = TreeManager.resolve_version(self.config, self.version_tag)
        metadata, raw_doc = tm.load_config_version_document(self.version_tag)

        self.evaluate(raw_doc, metadata)

        return {
            "path": self.config.path,
            "version": version_obj.version,
            "requested_version": self.version_tag,
            "parameters": self.parameters_meta,
        }
