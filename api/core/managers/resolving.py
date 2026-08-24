"""Per-config resolving pipeline: parameters → extend → render → cast.

Implements the design described in ``docs/resolving-*.md``.

Each :class:`ResolvePipelineManager` instance resolves **one** Config through
the documented pipeline steps:

    1. Load YAML body
    2. Pop and validate the ``_ocmo`` metadata block (strip it from data)
    3. Apply parameters (``{!param}`` placeholders + ``{!omit}``)
    4. Apply ``_ocmo.name`` (single-output)
    5. Apply ``_ocmo.extend`` (accumulate / distribute / align)
    6. Apply ``_ocmo.render`` (distribute / align) — incompatible with cast
    7. Apply cast (priority: ``?cast=`` → resolver default → ``_ocmo.cast`` → yaml)

Orchestration (path classification, artifact storage, cache, mark-stable,
download URLs, folder iteration) lives in
:class:`~.resolution.ResolutionManager`.

Recursive sub-resolves (``extend.configs`` / ``render.templates``) construct
new :class:`ResolvePipelineManager` instances; their
:attr:`_participants` lists are merged into the parent's so the calling
orchestrator has a complete flat list for short-circuit cache validation.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from django.conf import settings
from django.core.exceptions import ValidationError
from jinja2 import TemplateError
from ruamel.yaml import YAML

from ..decorators import PermCheck, arg, require_permissions
from ..exceptions import (
    CannotCast,
    CannotResolveConfig,
    CapabilityDenied,
    InvalidCastOption,
    NotFound,
    TemplateRenderError,
    UnknownCastFormat,
    UnknownCastOption,
)
from ..models import Config, Template, TreeItem
from ..schemas import (
    ConfigCastSchema,
    ConfigExtendRefSchema,
    ConfigExtendSchema,
    ConfigOcmoMetadataSchema,
    ConfigRenderSchema,
    normalize_extend_ref,
)
from ..shortcuts import (
    SelectorLookupError,
    embed_at_path,
    eval_selector,
    json_path,
    make_template_environment,
    parse_ref,
    resolve_relative_path,
)
from ..utils.deep_merge import deep_merge, strip_omit
from .auth import AuthManager
from .cast import CastManager
from .config_validation import ConfigValidationManager
from .resolve_parameters import ResolveParametersManager
from .tree import TreeManager
from .tree_capabilities import normalize_tree_path

logger = logging.getLogger(__name__)


def effective_cast(
    override_fmt: str | None,
    override_opts: dict[str, Any] | None,
    metadata_cast,  # ConfigCastSchema | None
) -> tuple[str, dict[str, Any]]:
    """Compute the effective (format, options) for casting one resolved output.

    Priority: caller override > per-config _ocmo.cast default > yaml.

    When the override format matches the metadata format, options are merged
    (override wins per key).  This mirrors the logic inside
    ``ResolvePipelineManager._effective_cast`` and must stay identical to it.
    """
    if override_fmt:
        opts: dict[str, Any] = dict(override_opts or {})
        if metadata_cast is not None and metadata_cast.get("format") == override_fmt:
            merged = dict(metadata_cast.get("options") or {})
            merged.update(opts)
            opts = merged
        return override_fmt, opts
    if metadata_cast is not None:
        return metadata_cast["format"], dict(metadata_cast.get("options") or {})
    return "yaml", {}


@dataclass
class CacheParticipant:
    """One resolved entity that participated in a config's resolution chain.

    Stored in the short-circuit cache entry so the cache manager can
    revalidate whether each participant's ref still resolves to the same
    version (i.e. nothing has changed).
    """

    kind: str  # "config" | "template" | "secret"
    path: str
    ref: str  # original version reference (e.g. "latest", "stable", "3")
    version: int  # resolved version number
    from_cache: bool = False


@dataclass
class _DraftVersion:
    data: str
    version: int = 0


@dataclass
class _MockConfig:
    path: str
    name: str


class _ResolvedOutput:
    """In-flight resolved item (data still in memory; not yet stored)."""

    __slots__ = ("name", "version", "format", "data_text", "raw_data", "trace", "rendered")

    def __init__(
        self,
        *,
        name: str,
        version: int,
        format: str,
        data_text: str | None,
        raw_data: Any = None,
        trace: dict | None = None,
        rendered: bool = False,
    ):
        self.name = name
        self.version = version
        self.format = format
        self.data_text = data_text  # finalized bytes-string (after cast/render)
        self.raw_data = raw_data  # pre-cast YAML data (used when re-merged from extend)
        self.trace = trace if trace is not None else {}
        self.rendered = rendered  # True for render-pipeline outputs; never re-cast


class ResolvePipelineManager:
    """Resolve **one** Config through the _ocmo pipeline end-to-end.

    Parameters
    ----------
    namespace:
        ``Namespace`` instance (already loaded).
    path:
        Path of the Config to resolve.
    version_ref:
        Tag name, ``latest``, ``stable``, or numeric version string.
    dynamic_params:
        Caller-supplied dynamic parameter values (raw strings from query).
    cast_override:
        Format override (from ``?cast=`` or resolver default cast).
    cast_options_override:
        Format options override (from ``?cast_option_*=`` or resolver defaults).
    """

    _OCMO_NAME_HEADER = re.compile(r"^#\s*ocmo\.name:\s*(.+)\s*$")

    def __init__(
        self,
        namespace,
        path: str,
        version_ref: str = "latest",
        *,
        dynamic_params: dict[str, Any] | None = None,
        cast_override: str | None = None,
        cast_options_override: dict[str, Any] | None = None,
        auth: AuthManager | None = None,
        no_creds: bool = False,
        draft_content: str | None = None,
        config_obj: Config | _MockConfig | None = None,
    ):
        self.namespace = namespace
        self.auth = auth
        normalized_path = path.strip("/")
        if draft_content is not None:
            if config_obj is not None:
                self.config_obj = config_obj
            else:
                try:
                    self.config_obj = TreeManager(namespace, normalized_path, auth=None).get_or_raise(["config"])
                except (TreeItem.DoesNotExist, NotFound):
                    name = normalized_path.split("/")[-1]
                    self.config_obj = _MockConfig(path=normalized_path, name=name)
            self.version_obj = _DraftVersion(data=draft_content, version=0)
            self.requested_version = "draft"
        elif config_obj is not None:
            self.config_obj = config_obj
            self.version_obj = TreeManager.resolve_version(self.config_obj, version_ref)
            self.requested_version = version_ref
        else:
            self.config_obj = TreeManager(namespace, normalized_path, auth=None).get_or_raise(["config"])
            self.version_obj = TreeManager.resolve_version(self.config_obj, version_ref)
            self.requested_version = version_ref
        parent_segments = self.config_obj.path.split("/")[:-1]
        self.base_folder = "/".join(parent_segments)
        self.dynamic_params = dict(dynamic_params or {})
        self.cast_override = cast_override
        self.cast_options_override = cast_options_override or {}
        self.no_creds = no_creds

        self._yaml = YAML()
        self._yaml.preserve_quotes = True

        # Flat list of every Config / Template / Secret consulted during this
        # resolution (including recursive sub-resolves). Populated during
        # resolve() / resolve_data_only(); read by ResolutionManager for cache.
        self._participants: list[CacheParticipant] = []

        # Per-config _ocmo.cast default, captured during the top-level
        # _resolve_recursive call. None until resolve() completes.
        self.metadata_cast: Any | None = None

    @staticmethod
    def resolve_webhooks_config(
        namespace,
    ) -> tuple[dict[str, Any], frozenset[str]] | None:
        """Resolve ``_webhooks`` config body and consulted secret paths."""
        version_info = TreeManager.get_webhooks_config_version(namespace)
        if version_info is None:
            return None
        tag, _version_number = version_info
        try:
            resolve_mgr = ResolvePipelineManager(namespace, "_webhooks", tag, auth=None)
            items = resolve_mgr.resolve_data_only(chain=[])
            resolved_body = items[0]["data"] if items else {}
            secret_paths = frozenset(
                normalize_tree_path(p.path) for p in resolve_mgr._participants if p.kind == "secret"
            )
            return resolved_body, secret_paths
        except Exception as exc:
            logger.warning(
                "Failed to resolve webhooks config for %s: %s",
                namespace.name,
                exc,
            )
            return None

    # ----- public API -----

    @require_permissions(PermCheck("config:resolve", resource=lambda self: self.config_obj.path))
    def resolve(self) -> list[_ResolvedOutput]:
        """Resolve this Config and return a list of finalized outputs."""
        return self._resolve_recursive(chain=[])

    @require_permissions(PermCheck("config:resolve", resource=lambda self: self.config_obj.path))
    def resolve_data_only(self, chain: list[str]) -> list[dict[str, Any]]:
        """Return ``[{name, data, trace}, ...]`` for use as an extend source.

        ``data`` is the structured Python dict/list (pre-cast), so it can be
        merged into the calling config.
        """
        outputs = self._resolve_recursive(chain=chain, want_data=True)
        return [{"name": o.name, "data": o.raw_data, "trace": o.trace} for o in outputs]

    @require_permissions(PermCheck("config:resolve", resource=arg("resolved_path")))
    def load_render_template(self, resolved_path: str, version_ref: str) -> Template:
        """Load a template for render after ``config:resolve`` permission check."""
        tmpl = TreeManager(self.namespace, resolved_path, auth=None).get_or_raise(["template"])
        return TreeManager.resolve_version(tmpl, version_ref)

    # ----- internals -----

    def _trace_key(self) -> str:
        return f"{self.config_obj.path}@{self.version_obj.version}"

    def _resolve_recursive(self, *, chain: list[str], want_data: bool = False) -> list[_ResolvedOutput]:
        # Depth + loop guard.
        if len(chain) >= settings.OCMO_MAX_CONFIG_RESOLVE_DEPTH:
            raise CannotResolveConfig(
                "Maximum config resolve depth "
                f"({settings.OCMO_MAX_CONFIG_RESOLVE_DEPTH}) reached. "
                f"Chain: {' -> '.join(chain)}"
            )
        my_key = self._trace_key()
        if my_key in chain:
            raise CannotResolveConfig(
                f"Recursion not allowed during configs resolving. Chain: {' -> '.join(chain)} -> {my_key}"
            )

        # Record this config as a cache participant.
        self._participants.append(
            CacheParticipant(
                kind="config",
                path=self.config_obj.path,
                ref=self.requested_version,
                version=self.version_obj.version,
            )
        )

        # 1–2) Load YAML body and extract & validate _ocmo
        try:
            metadata, raw_doc = ConfigValidationManager.parse_config_yaml_document(self.version_obj.data)
        except ValidationError as exc:
            raise CannotResolveConfig(f"Cannot resolve {self.config_obj.path}: {exc}") from exc

        # 3) Evaluate parameters and substitute into body + metadata fields.
        params_mgr = ResolveParametersManager(
            self.namespace,
            cast(Config, self.config_obj),
            base_folder=self.base_folder,
            version_tag=self.requested_version,
            version_number=self.version_obj.version,
            dynamic_params=self.dynamic_params,
            auth=self.auth,
            no_creds=self.no_creds,
        )
        data, metadata = params_mgr.apply(raw_doc, metadata)

        # Record resolved secrets as cache participants and add to trace.
        for sec in params_mgr.resolved_secrets:
            self._participants.append(
                CacheParticipant(
                    kind="secret",
                    path=sec["path"],
                    ref=sec["ref"],
                    version=sec["version"],
                )
            )

        # 4) Apply _ocmo.name (single-output default; multi-output naming
        #    happens inside extend/render below).
        own_name = self._initial_name(metadata)

        # 5) Build base output (this config's own data as one item).
        #    Keep the _OMIT sentinels around: extend may need them to drive
        #    dict-key removal and list-item omission during deep-merge; we
        #    strip them once at the end of the resolve.
        my_trace: dict[str, Any] = {}

        # Add resolved secrets as redacted trace entries.
        for sec in params_mgr.resolved_secrets:
            my_trace[f"secret:{sec['path']}@{sec['version']}"] = {}

        new_chain = chain + [my_key]
        outputs: list[_ResolvedOutput] = [
            _ResolvedOutput(
                name=own_name,
                version=self.version_obj.version,
                format="yaml",
                data_text=None,
                raw_data=data,
                trace=my_trace,
            )
        ]

        # 6) Extend
        if metadata.extend is not None:
            outputs = self._apply_extend(metadata.extend, outputs, new_chain, my_trace)
        else:
            # No extend → still need to drop any leftover _OMIT sentinels
            # that came from {!omit} placeholders inside this config.
            outputs[0].raw_data = strip_omit(outputs[0].raw_data)

        # 7) Render (incompatible with cast — schema enforces this).
        if metadata.render is not None:
            outputs = self._apply_render(metadata.render, outputs, new_chain, my_trace)
            if want_data:
                for out in outputs:
                    out.raw_data = out.data_text
                return outputs
            return outputs

        # Capture _ocmo.cast for the top-level caller (not recursive sub-resolves).
        if not chain:
            self.metadata_cast = metadata.cast

        # 8) Cast (priority: cast_override → metadata.cast → yaml)
        cast_fmt, cast_opts = self._effective_cast(metadata.cast)
        if want_data:
            return outputs

        caster = CastManager(cast_fmt, cast_opts, source_label=self.config_obj.path)
        for out in outputs:
            try:
                out.format = cast_fmt
                out.data_text = caster.cast(out.raw_data)
            except (
                UnknownCastFormat,
                CannotCast,
                UnknownCastOption,
                InvalidCastOption,
            ):
                raise

        return outputs

    def _initial_name(self, metadata: ConfigOcmoMetadataSchema) -> str:
        if metadata.name:
            # Single-config naming rule: keep only the last segment when the
            # value contains '/'.
            if "/" in metadata.name:
                return metadata.name.split("/")[-1]
            return metadata.name
        return self.config_obj.name

    # ----- extend -----

    def _prepare_extend_fragment(
        self,
        ref: ConfigExtendRefSchema,
        raw_data: Any,
        *,
        source_path: str,
    ) -> Any:
        if ref.key:
            try:
                value = eval_selector(raw_data, ref.key)
            except SelectorLookupError as exc:
                raise CannotResolveConfig(f"Extend key {exc.expr!r} not found in config {source_path!r}") from exc
        else:
            value = raw_data
        if ref.as_:
            return embed_at_path(ref.as_, value)
        if value == []:
            return {}
        return value

    def _apply_extend(
        self,
        extend: ConfigExtendSchema,
        outputs: list[_ResolvedOutput],
        chain: list[str],
        trace: dict[str, Any],
    ) -> list[_ResolvedOutput]:
        assert len(outputs) == 1, "extend operates on this config's single output"
        current = outputs[0]
        current_data = current.raw_data
        mode = extend.mode

        # Resolve each entry — each may itself expand to multiple outputs.
        base_outputs: list[_ResolvedOutput] = []
        for ref in extend.configs:
            norm = normalize_extend_ref(ref)
            path, version = parse_ref(norm.path)
            resolved_path = resolve_relative_path(self.base_folder, path)
            if not TreeManager(self.namespace, resolved_path, auth=self.auth).is_extend_target:
                raise CapabilityDenied(f"Config '{resolved_path}' cannot be used in extend")
            sub_mgr = ResolvePipelineManager(
                self.namespace,
                resolved_path,
                version,
                auth=self.auth,
                no_creds=self.no_creds,
            )
            sub_items = sub_mgr.resolve_data_only(chain=chain)
            # Merge sub-manager participants into ours.
            self._participants.extend(sub_mgr._participants)
            ref_trace: dict[str, Any] = {}
            if norm.key is not None:
                ref_trace["key"] = norm.key
            if norm.as_ is not None:
                ref_trace["as"] = norm.as_
            trace_entry = self._collect_trace(sub_items)
            if ref_trace:
                trace_entry = {**trace_entry, **ref_trace}
            trace[sub_mgr._trace_key()] = trace_entry
            for item in sub_items:
                fragment = self._prepare_extend_fragment(
                    norm,
                    item["data"],
                    source_path=resolved_path,
                )
                base_outputs.append(
                    _ResolvedOutput(
                        name=item["name"],
                        version=sub_mgr.version_obj.version,
                        format="yaml",
                        data_text=None,
                        raw_data=fragment,
                        trace=item["trace"],
                    )
                )

        if mode == "accumulate":
            merged: Any = {}
            for b in base_outputs:
                merged = deep_merge(merged, b.raw_data)
            merged = deep_merge(merged, current_data)
            current.raw_data = strip_omit(merged)
            return [current]

        # Both distribute and align need the "patch" payload from current data.
        if extend.by:
            patch_value = json_path(current_data, extend.by)
        else:
            patch_value = current_data

        if mode == "distribute":
            results: list[_ResolvedOutput] = []
            for b in base_outputs:
                merged = deep_merge(b.raw_data, patch_value)
                results.append(
                    _ResolvedOutput(
                        name=b.name,
                        version=b.version,
                        format="yaml",
                        data_text=None,
                        raw_data=strip_omit(merged),
                        trace=trace,
                    )
                )
            return results

        if mode == "align":
            if not isinstance(patch_value, list):
                raise CannotResolveConfig(f"extend mode 'align' requires by={extend.by!r} to resolve to a list")
            if len(patch_value) != len(base_outputs):
                raise CannotResolveConfig(
                    f"extend 'align' length mismatch: {len(base_outputs)} configs vs "
                    f"{len(patch_value)} items at {extend.by!r}"
                )
            results = []
            for b, patch in zip(base_outputs, patch_value):
                merged = deep_merge(b.raw_data, patch)
                results.append(
                    _ResolvedOutput(
                        name=b.name,
                        version=b.version,
                        format="yaml",
                        data_text=None,
                        raw_data=strip_omit(merged),
                        trace=trace,
                    )
                )
            return results

        raise CannotResolveConfig(f"Unsupported extend mode {mode!r}")

    @staticmethod
    def _collect_trace(items: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for item in items:
            merged.update(item.get("trace") or {})
        return merged

    # ----- render -----

    def _load_render_templates(
        self,
        render: ConfigRenderSchema,
        trace: dict[str, Any],
    ) -> list[tuple[str, str, int, str]]:
        """Load template bodies referenced by ``render.templates``."""
        templates: list[tuple[str, str, int, str]] = []
        for ref in render.templates:
            path, version = parse_ref(ref)
            resolved_path = resolve_relative_path(self.base_folder, path)
            version_obj = self.load_render_template(resolved_path, version)
            trace[f"{resolved_path}@{version_obj.version}"] = {}
            self._participants.append(
                CacheParticipant(
                    kind="template",
                    path=resolved_path,
                    ref=version,
                    version=version_obj.version,
                )
            )
            templates.append((ref, resolved_path, version_obj.version, version_obj.data))
        return templates

    def _render_one_output(
        self,
        render: ConfigRenderSchema,
        output: _ResolvedOutput,
        templates: list[tuple[str, str, int, str]],
        env,
        trace: dict[str, Any],
    ) -> list[_ResolvedOutput]:
        """Render ``templates`` against one resolved config output."""
        data = output.raw_data

        if render.mode == "distribute":
            if render.by:
                bucket = json_path(data, render.by)
                if not isinstance(bucket, list):
                    raise CannotResolveConfig(f"render mode 'distribute' with by={render.by!r} requires a list")
                merged_ctx: Any = {}
                for entry in bucket:
                    merged_ctx = deep_merge(merged_ctx, entry)
                contexts = [merged_ctx] * len(templates)
            else:
                contexts = [data] * len(templates)
        else:  # align
            if render.by is None:
                raise CannotResolveConfig("render mode 'align' requires by")
            bucket = json_path(data, render.by)
            if not isinstance(bucket, list):
                raise CannotResolveConfig(f"render mode 'align' requires by={render.by!r} to resolve to a list")
            if len(bucket) != len(templates):
                raise CannotResolveConfig(
                    f"render 'align' length mismatch: {len(templates)} templates vs "
                    f"{len(bucket)} entries at {render.by!r}"
                )
            contexts = bucket

        results: list[_ResolvedOutput] = []
        for (_orig_ref, tmpl_path, tmpl_version, body), ctx in zip(templates, contexts):
            try:
                rendered = env.from_string(body).render(**(ctx if isinstance(ctx, Mapping) else {"_": ctx}))
            except TemplateError as exc:
                raise TemplateRenderError(f"Template {tmpl_path}@{tmpl_version} render failed: {exc}") from exc

            name = tmpl_path.split("/")[-1]
            first_line, _, rest = rendered.partition("\n")
            m = self._OCMO_NAME_HEADER.match(first_line)
            if m:
                name = m.group(1).strip()
                rendered = rest

            results.append(
                _ResolvedOutput(
                    name=name,
                    version=output.version,
                    format="raw",
                    data_text=rendered,
                    raw_data=rendered,
                    trace=trace,
                    rendered=True,
                )
            )
        return results

    def _apply_render(
        self,
        render: ConfigRenderSchema,
        outputs: list[_ResolvedOutput],
        chain: list[str],
        trace: dict[str, Any],
    ) -> list[_ResolvedOutput]:
        """Render each resolved config output (e.g. from extend distribute/align)."""
        if not outputs:
            return []

        templates = self._load_render_templates(render, trace)
        env = make_template_environment()

        results: list[_ResolvedOutput] = []
        for output in outputs:
            results.extend(self._render_one_output(render, output, templates, env, trace))
        return results

    # ----- cast -----

    def _effective_cast(self, metadata_cast: ConfigCastSchema | None) -> tuple[str, dict[str, Any]]:
        meta_dict = (
            {
                "format": metadata_cast.format,
                "options": dict(metadata_cast.options or {}),
            }
            if metadata_cast is not None
            else None
        )
        return effective_cast(self.cast_override, self.cast_options_override, meta_dict)
