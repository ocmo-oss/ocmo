"""Resolve orchestration: path classification, cache, artifacts, folder iteration.

This module owns everything that is NOT per-config ``_ocmo`` pipeline logic:

- Scope-prefixing of the requested path for resolver-authenticated requests.
- Classifying the effective path as a single Config or a folder subtree.
- Applying resolver ``include``/``exclude`` glob filters for folder resolution.
- Two-layer short-circuit cache via :class:`.resolve_cache.ResolveCacheManager`.
- Calling :class:`.resolving.ResolvePipelineManager` for the actual pipeline.
- Storing resolved artifacts and minting signed download URLs.
- Assembling the ``ResolveResponseSchema``-compatible response dict.
- ``mark-stable`` promotion of the ``stable`` tag on resolved Config roots.
- Parsing ``param_*`` / ``cast_option_*`` query-string parameters.
- Wiring resolver default cast format and dynamic-parameter defaults when the
  caller is authenticated as a Resolver.

Usage (from the API endpoint)::

    ns = NamespaceManager(namespace).get_or_raise()
    mgr = ResolutionManager(
        ns, path,
        auth=auth,
        query_params=request.GET,
        base_url=request.build_absolute_uri("/"),
        version=version, cast=cast,
        trace_only=trace_only, promote_stable=mark_stable,
    )
    result = mgr.resolve()
    request._resolve_cache_status = mgr.cache_status

For the scope-prefixing helper used by both resolve endpoints::

    effective_path, resolver_mgr = scoped_resolve_path(ns, path, auth)

Draft resolve (unsaved YAML)::

    mgr = ResolutionManager(
        ns, path, auth=auth, query_params=request.GET,
        base_url=request.build_absolute_uri("/"),
        cast=cast, trace_only=trace_only, no_creds=no_creds,
        draft_content=draft_yaml,
    )
    result = mgr.resolve()
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from ..decorators import PermCheck, arg, require_permissions, webhook
from ..exceptions import CannotResolveConfig, CapabilityDenied, PermissionDenied
from ..models import Config, TreeItem
from ..schemas.cast_options import CAST_FORMATS
from ..shortcuts import config_path_relative_to_folder, match_resolver_glob
from .artifacts import ArtifactsManager, get_backend, mint_token, sweep_fs_artifacts_if_due
from .audit import AuditManager
from .auth import AuthManager
from .cast import CastManager
from .resolve_cache import ResolveCacheManager
from .resolver import ResolverManager
from .resolving import CacheParticipant, ResolvePipelineManager, effective_cast
from .tree import TreeManager
from .tree_capabilities import compute_tree_capabilities

logger = logging.getLogger(__name__)

_PARAM_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")
_MAX_DYNAMIC_PARAMS = 50
_MAX_QUERY_VALUE_LEN = 4096

_RESOLVER_HOOK_FIELDS = (
    "validate",
    "validate_all",
    "post_resolve",
    "post_resolve_all",
)

_RESERVED_QUERY_KEYS = frozenset(
    {
        "version",
        "cast",
        "trace_only",
        "mark-stable",
        "ignore-configs-with-missing-tags",
        "no-creds",
        "token",
        "page",
        "limit",
        "offset",
    }
)


def validate_cast_format(cast: str | None) -> str | None:
    if cast is None:
        return None
    if cast not in CAST_FORMATS:
        raise ValidationError(f"Unknown cast format {cast!r}")
    return cast


def parse_query_params(query_params) -> tuple[dict[str, Any], dict[str, Any]]:
    """Pull ``param_*`` and ``cast_option_*`` values from a query-string mapping."""
    dynamic_params: dict[str, Any] = {}
    cast_options: dict[str, Any] = {}
    dynamic_count = 0
    for key, value in query_params.items():
        if key in _RESERVED_QUERY_KEYS:
            continue
        val = value[0] if isinstance(value, list) else value
        if val is not None and len(str(val)) > _MAX_QUERY_VALUE_LEN:
            raise ValidationError(f"Query parameter {key!r} exceeds maximum length of {_MAX_QUERY_VALUE_LEN}")
        if key.startswith("param_"):
            name = key[len("param_") :]
            if not _PARAM_NAME_RE.match(name):
                raise ValidationError(f"Invalid dynamic parameter name {name!r}")
            dynamic_count += 1
            if dynamic_count > _MAX_DYNAMIC_PARAMS:
                raise ValidationError("Too many param_* query parameters")
            dynamic_params[name] = val
        elif key.startswith("cast_option_"):
            cast_options[key[len("cast_option_") :]] = val
    return dynamic_params, cast_options


# HTTP proxies and URL normalizers drop a lone ``.`` path segment before the
# request reaches Django. Clients send ``@`` for resolver scope-root instead.
RESOLVE_SCOPE_ROOT_WIRE = "@"


def decode_resolve_path(path: str) -> str:
    """Map wire-safe resolve path segments back to logical paths."""
    if path.strip("/") in (RESOLVE_SCOPE_ROOT_WIRE, "."):
        return "."
    return path


def scoped_resolve_path(
    namespace,
    requested_path: str,
    auth: AuthManager | None,
) -> tuple[str, ResolverManager | None]:
    """Return the effective tree path and an optional ResolverManager.

    - Resolver-authenticated: path is relative to the resolver's scope.
      ``'.'`` resolves to the scope root itself.
    - User/OAuth-authenticated: path must be a full namespace-relative path.
      Passing ``'.'`` is rejected with ``ValidationError``.
    """
    if auth is not None and auth.is_resolver:
        rm = ResolverManager(namespace, auth)
        return rm.scoped_path(requested_path), rm
    if requested_path.strip("/") == ".":
        raise ValidationError("'.' is only valid for resolver-authenticated requests")
    return requested_path.strip("/"), None


# ---------------------------------------------------------------------------
# ResolutionManager
# ---------------------------------------------------------------------------


class ResolutionManager:
    """Orchestrate resolution of a Config or folder subtree.

    Construct once per request; call :meth:`resolve` to run.

    Parameters
    ----------
    namespace:
        ``Namespace`` model instance (already loaded).
    path:
        Requested path string (namespace-relative for user auth; scope-relative
        for resolver auth — prefixing is applied in ``__init__``).
    auth:
        ``AuthManager`` for the current request identity.
    query_params:
        Query-string mapping (``request.GET``).
    base_url:
        Absolute base URL used to build download URLs
        (``request.build_absolute_uri("/")``)
    version:
        Version tag or number string (default ``"latest"``).
    cast:
        Cast format override (highest priority, from ``?cast=``).
    trace_only:
        When ``True``, runs the full dependency walk but skips artifact storage.
    promote_stable:
        When ``True``, advances the ``stable`` tag on resolved Config roots.
    ignore_configs_with_missing_tags:
        When ``True`` and the target is a folder, skip Configs whose requested
        ``version`` cannot be resolved instead of failing the whole request.
    no_creds:
        When ``True``, secret parameters use the dummy value
        ``<secret-value-placeholder>`` without fetching secrets or requiring
        ``secret:resolve``.
    draft_content:
        When set, resolve unsaved YAML at ``path`` instead of a stored version.
        The path need not exist. Resolver auth is rejected; no cache or
        ``stable`` promotion.
    """

    path: str
    resolver_mgr: ResolverManager | None
    resolver_config: dict[str, Any]
    item: TreeItem | None

    def __init__(
        self,
        namespace,
        path: str,
        *,
        auth: AuthManager,
        query_params,
        base_url: str,
        version: str = "latest",
        cast: str | None = None,
        trace_only: bool = False,
        promote_stable: bool = False,
        ignore_configs_with_missing_tags: bool = False,
        no_creds: bool = False,
        draft_content: str | None = None,
    ) -> None:
        self.auth = auth
        self.namespace = namespace
        self.trace_only = trace_only
        self.no_creds = no_creds
        self.base_url = base_url.rstrip("/")
        self.cache_status = "miss"
        self.draft_content = draft_content

        raw_dynamic_params, raw_cast_options = parse_query_params(query_params)

        if draft_content is not None:
            self._init_draft_resolve(
                path,
                cast=cast,
                raw_dynamic_params=raw_dynamic_params,
                raw_cast_options=raw_cast_options,
            )
        else:
            self._init_real_resolve(
                path,
                version=version,
                cast=cast,
                promote_stable=promote_stable,
                ignore_configs_with_missing_tags=ignore_configs_with_missing_tags,
                raw_dynamic_params=raw_dynamic_params,
                raw_cast_options=raw_cast_options,
            )

        self.identity = ArtifactsManager.identity_from_auth(auth)

    def _init_draft_resolve(
        self,
        path: str,
        *,
        cast: str | None,
        raw_dynamic_params: dict[str, Any],
        raw_cast_options: dict[str, Any],
    ) -> None:
        if self.auth.is_resolver:
            raise PermissionDenied("Draft resolve requires user authentication")
        self.path = path.strip("/")
        caps = compute_tree_capabilities(self.namespace, self.path, self.auth)
        if not caps.is_resolvable:
            raise PermissionDenied(f"Config '{self.path}' cannot be resolved at this path")
        self.resolver_mgr = None
        self.resolver_config = {}
        self.cast = cast
        self.cast_options = (raw_cast_options or None) if cast else None
        self.dynamic_params = raw_dynamic_params or None
        self.version = "draft"
        self.promote_stable = False
        self.ignore_configs_with_missing_tags = False
        self.item = None

    def _init_real_resolve(
        self,
        path: str,
        *,
        version: str,
        cast: str | None,
        promote_stable: bool,
        ignore_configs_with_missing_tags: bool,
        raw_dynamic_params: dict[str, Any],
        raw_cast_options: dict[str, Any],
    ) -> None:
        self.path, self.resolver_mgr = scoped_resolve_path(self.namespace, path, self.auth)
        self.item = TreeManager(self.namespace, self.path, auth=None).get_or_raise()

        self.resolver_config = {}
        effective_cast_fmt = cast
        effective_cast_options: dict[str, Any] = dict(raw_cast_options)
        effective_dynamic_params: dict[str, Any] = dict(raw_dynamic_params)

        if self.resolver_mgr is not None:
            rc = self.resolver_mgr.configuration
            self.resolver_config = rc.model_dump(exclude_none=True)

            if cast is None and rc.cast is not None:
                effective_cast_fmt = rc.cast.format
                resolver_opts = dict(rc.cast.options or {})
                effective_cast_options = {**resolver_opts, **effective_cast_options}

            merged_params: dict[str, Any] = dict(rc.parameters or {})
            merged_params.update(effective_dynamic_params)
            effective_dynamic_params = merged_params

        self.cast = effective_cast_fmt
        self.cast_options = (effective_cast_options or None) if effective_cast_fmt else None
        self.dynamic_params = effective_dynamic_params or None
        self.version = version
        self.promote_stable = promote_stable
        self.ignore_configs_with_missing_tags = ignore_configs_with_missing_tags

    def _participants_from_cache(self, raw_participants: list[dict]) -> list[CacheParticipant]:
        return [
            CacheParticipant(
                kind=p["kind"],
                path=p["path"],
                ref=p.get("ref", ""),
                version=p["version"],
                from_cache=True,
            )
            for p in raw_participants
        ]

    def _require_cache_entry_permissions(self, entry: dict) -> None:
        if self.auth is None:
            return
        self.auth.permissions(self.namespace).require_resolve_participants(
            entry.get("participants", []),
            no_creds=self.no_creds,
        )

    def _record_resolve_audit(
        self,
        config_path: str,
        participants: list[CacheParticipant],
        *,
        error: str | None = None,
    ) -> None:
        with AuditManager.resolve_request(config_path) as rec:
            rec.participants = participants
            rec.error = error

    # ----- public entry point -----

    def resolve(self) -> dict[str, Any]:
        """Resolve the target path (single Config or folder subtree).

        When :attr:`draft_content` is set, resolves unsaved YAML at
        :attr:`path` without persisting it.

        Returns the structured dict expected by ``ResolveResponseSchema``.
        Sets ``self.cache_status`` to ``"hit"``, ``"cast"``, or ``"miss"``.
        """
        if self.draft_content is not None:
            return self._resolve_draft()

        assert self.item is not None

        sweep_fs_artifacts_if_due()

        if self.item.node_type == "folder":
            configs = TreeManager.for_item(self.namespace, self.item, auth=self.auth).list_configs_under_folder(
                ignore_configs_with_missing_tags=self.ignore_configs_with_missing_tags,
                version=self.version,
            )
            configs = self._filter_configs(configs)

            items_out: list[dict[str, Any]] = []
            promotions: list[tuple[str, int]] = []
            for cfg in configs:
                outputs = self.resolve_at_path(
                    cfg.path,
                    folder_base=self.path,
                    request_path=self.path,
                    bypass_cache=self.promote_stable,
                    config=cfg,
                )
                items_out.extend(outputs)
                if self.promote_stable and not self.trace_only and outputs:
                    promotions.append((cfg.path, outputs[0]["version"]))
            if promotions:
                self._promote_stable_tags(promotions)
            result = self._wrap_response(
                items_out,
                trace_only=self.trace_only,
                root=None,
                resolver=self._effective_resolver_payload(),
            )
            self.cache_status = self._cache_status(items_out)
            return result

        if self.item.node_type != "config":
            raise CannotResolveConfig(f"{self.item.node_type} {self.path!r} cannot be resolved (only Config or Folder)")

        outputs = self.resolve_at_path(
            self.path,
            folder_base=None,
            request_path=self.path,
            bypass_cache=self.promote_stable,
        )

        if self.promote_stable and not self.trace_only and outputs:
            self._promote_stable_tags([(self.path, outputs[0]["version"])])

        root_info = None
        if self.trace_only:
            root_info = {
                "path": self.path,
                "version": outputs[0]["version"] if outputs else None,
                "requested_version": self.version,
            }
        result = self._wrap_response(
            outputs,
            trace_only=self.trace_only,
            root=root_info,
            resolver=self._effective_resolver_payload(),
        )
        self.cache_status = self._cache_status(outputs)
        return result

    def _resolve_draft(self) -> dict[str, Any]:
        outputs = self.resolve_at_path(
            self.path,
            folder_base=None,
            request_path=self.path,
        )
        root_info = None
        if self.trace_only:
            root_info = {
                "path": self.path,
                "version": 0,
                "requested_version": "draft",
            }
        return self._wrap_response(
            outputs,
            trace_only=self.trace_only,
            root=root_info,
            resolver=self._effective_resolver_payload(),
        )

    # ----- single-config resolution (two-layer cache-aware) -----

    @webhook(
        "config.resolved",
        path=lambda self, result, bound: bound["config_path"],
        version=lambda self, result, bound: result[0].get("version") if result else None,
        skip_when=lambda self, result, bound: self.trace_only or not result or self.draft_content is not None,
    )
    @require_permissions(PermCheck("config:resolve", resource=arg("config_path")))
    def resolve_at_path(
        self,
        config_path: str,
        *,
        folder_base: str | None,
        request_path: str,
        bypass_cache: bool = False,
        config: Config | None = None,
    ) -> list[dict[str, Any]]:
        """Resolve one Config path with permission and capability gates."""
        if config is not None:
            tm = TreeManager.for_item(self.namespace, config, auth=self.auth)
        else:
            tm = TreeManager(self.namespace, config_path, auth=self.auth)
        if not tm.is_resolvable:
            raise CapabilityDenied(
                f"Config by path '{config_path}' can't be resolved without namespace level write permission"
            )
        if not tm.is_direct_resolve_target:
            raise CapabilityDenied(f"Config '{config_path}' is outside resolver scope and cannot be resolved directly")

        # trace_only or bypass_cache or draft_content: always run the full pipeline, skip cache.
        if self.trace_only or bypass_cache or self.draft_content is not None:
            items = self._run_pipeline(
                config_path,
                folder_base=folder_base,
                request_path=request_path,
                draft_content=self.draft_content,
                config_obj=config,
            )
            for it in items:
                it["_cache"] = "miss"
            return items

        # --- Layer 2: artifact cache (includes cast in key) ---
        art_key = ResolveCacheManager.make_artifact_key(
            self.namespace.name,
            config_path,
            self.version,
            self.cast,
            self.cast_options,
            self.dynamic_params,
            no_creds=self.no_creds,
        )
        art_entry = ResolveCacheManager.get(art_key)
        if art_entry is not None and ResolveCacheManager.is_valid(art_entry, self.namespace):
            self._require_cache_entry_permissions(art_entry)
            items = self._items_from_artifact_entry(art_entry, config_path, folder_base, request_path, _cache="hit")
            self._record_resolve_audit(
                config_path,
                self._participants_from_cache(art_entry.get("participants", [])),
            )
            return items

        # --- Layer 1: resolution cache (cast-independent) ---
        res_key = ResolveCacheManager.make_resolution_key(
            self.namespace.name,
            config_path,
            self.version,
            self.dynamic_params,
            no_creds=self.no_creds,
        )
        res_entry = ResolveCacheManager.get(res_key)
        if res_entry is not None and ResolveCacheManager.participants_valid(res_entry, self.namespace):
            self._require_cache_entry_permissions(res_entry)
            items = self._cast_from_resolution_entry(
                res_entry,
                config_path,
                folder_base,
                request_path,
                art_key=art_key,
            )
            self._record_resolve_audit(
                config_path,
                self._participants_from_cache(res_entry.get("participants", [])),
            )
            return items

        # --- Full pipeline ---
        items = self._run_pipeline(
            config_path,
            folder_base=folder_base,
            request_path=request_path,
            art_key=art_key,
            res_key=res_key,
            config_obj=config,
        )
        for it in items:
            it["_cache"] = "miss"
        return items

    def _items_from_artifact_entry(
        self,
        entry: dict[str, Any],
        config_path: str,
        folder_base: str | None,
        request_path: str,
        *,
        _cache: str,
    ) -> list[dict[str, Any]]:
        """Build response items from a Layer 2 artifact cache entry."""
        items: list[dict[str, Any]] = []
        for out in entry["outputs"]:
            name = self._apply_folder_naming(out["name"], config_path, folder_base)
            token = mint_token(
                artifact_id=out["artifact_id"],
                namespace=self.namespace.name,
                item_path=request_path,
                identity=self.identity,
            )
            url = self._build_download_url(request_path, token)
            items.append(
                {
                    "name": name,
                    "version": out["version"],
                    "format": out["format"],
                    "url": url,
                    "checksum": out["checksum"],
                    "trace": out["trace"],
                    "_cache": _cache,
                }
            )
        return items

    def _cast_from_resolution_entry(
        self,
        res_entry: dict[str, Any],
        config_path: str,
        folder_base: str | None,
        request_path: str,
        *,
        art_key: str,
    ) -> list[dict[str, Any]]:
        """Cast Layer 1 pre-cast data, store artifacts, write Layer 2."""
        fmt, opts = effective_cast(
            self.cast,
            self.cast_options,
            res_entry.get("metadata_cast"),
        )
        caster = CastManager(fmt, opts, source_label=config_path)
        backend = get_backend()

        items: list[dict[str, Any]] = []
        art_outputs: list[dict[str, Any]] = []

        for out in res_entry["outputs"]:
            name = self._apply_folder_naming(out["name"], config_path, folder_base)

            if out.get("rendered"):
                # Render outputs are already finalized text; re-cast is not applicable.
                output_fmt = out["format"]
                text = out["raw_data"]
            else:
                output_fmt = fmt
                text = caster.cast(out["raw_data"])

            if isinstance(text, bytes):
                data_bytes = text
            elif isinstance(text, str):
                data_bytes = text.encode("utf-8")
            else:
                data_bytes = (text or "").encode("utf-8")

            artifact_id = backend.store(data_bytes)
            checksum = hashlib.sha256(data_bytes).hexdigest()
            token = mint_token(
                artifact_id=artifact_id,
                namespace=self.namespace.name,
                item_path=request_path,
                identity=self.identity,
            )
            url = self._build_download_url(request_path, token)

            items.append(
                {
                    "name": name,
                    "version": out["version"],
                    "format": output_fmt,
                    "url": url,
                    "checksum": checksum,
                    "trace": out["trace"],
                    "_cache": "cast",
                }
            )
            art_outputs.append(
                {
                    "name": out["name"],
                    "version": out["version"],
                    "format": output_fmt,
                    "artifact_id": artifact_id,
                    "checksum": checksum,
                    "trace": out["trace"],
                }
            )

        # Populate Layer 2 so the next identical-cast request is a pure L2 hit.
        ResolveCacheManager.set(
            art_key,
            {
                "outputs": art_outputs,
                "participants": res_entry["participants"],
            },
        )

        return items

    def _run_pipeline(
        self,
        config_path: str,
        *,
        folder_base: str | None,
        request_path: str,
        art_key: str | None = None,
        res_key: str | None = None,
        draft_content: str | None = None,
        config_obj: Config | None = None,
    ) -> list[dict[str, Any]]:
        mgr: ResolvePipelineManager | None = None
        items: list[dict[str, Any]] = []
        with AuditManager.resolve_request(config_path) as resolve_audit:
            try:
                mgr = ResolvePipelineManager(
                    self.namespace,
                    config_path,
                    self.version,
                    dynamic_params=self.dynamic_params,
                    cast_override=self.cast,
                    cast_options_override=self.cast_options,
                    auth=self.auth,
                    no_creds=self.no_creds,
                    draft_content=draft_content,
                    config_obj=config_obj,
                )
                pipeline_outputs = mgr.resolve()

                backend = get_backend() if not self.trace_only else None
                art_cache_outputs: list[dict[str, Any]] = []
                res_cache_outputs: list[dict[str, Any]] = []
                items = []

                for out in pipeline_outputs:
                    name = self._final_name(out.name, config_path, folder_base, mgr)
                    checksum = None
                    url = None
                    artifact_id = None

                    if not self.trace_only:
                        assert backend is not None
                        if isinstance(out.data_text, bytes):
                            data_bytes = out.data_text
                        elif isinstance(out.data_text, str):
                            data_bytes = out.data_text.encode("utf-8")
                        else:
                            data_bytes = (out.data_text or "").encode("utf-8")
                        artifact_id = backend.store(data_bytes)
                        checksum = hashlib.sha256(data_bytes).hexdigest()
                        token = mint_token(
                            artifact_id=artifact_id,
                            namespace=self.namespace.name,
                            item_path=request_path,
                            identity=self.identity,
                        )
                        url = self._build_download_url(request_path, token)
                        if draft_content is None:
                            art_cache_outputs.append(
                                {
                                    "name": out.name,
                                    "version": out.version,
                                    "format": out.format,
                                    "artifact_id": artifact_id,
                                    "checksum": checksum,
                                    "trace": out.trace,
                                }
                            )
                            res_cache_outputs.append(
                                {
                                    "name": out.name,
                                    "version": out.version,
                                    "rendered": out.rendered,
                                    "format": out.format,
                                    "raw_data": out.raw_data,
                                    "trace": out.trace,
                                }
                            )

                    items.append(
                        {
                            "name": name,
                            "version": out.version,
                            "format": out.format,
                            "url": url,
                            "checksum": checksum,
                            "trace": out.trace,
                        }
                    )

                if draft_content is None:
                    participants = [
                        {"kind": p.kind, "path": p.path, "ref": p.ref, "version": p.version} for p in mgr._participants
                    ]
                    has_secrets = any(p["kind"] == "secret" for p in participants)

                    if not self.trace_only and art_key and art_cache_outputs:
                        ResolveCacheManager.set(
                            art_key,
                            {
                                "outputs": art_cache_outputs,
                                "participants": participants,
                            },
                        )

                    # Write Layer 1 only when there are no secrets (avoids secret plaintext
                    # at-rest in the resolve cache store).
                    if not self.trace_only and res_key and res_cache_outputs and not has_secrets:
                        mc = mgr.metadata_cast
                        metadata_cast_dict = (
                            {"format": mc.format, "options": dict(mc.options or {})} if mc is not None else None
                        )
                        ResolveCacheManager.set(
                            res_key,
                            {
                                "metadata_cast": metadata_cast_dict,
                                "outputs": res_cache_outputs,
                                "participants": participants,
                            },
                        )

                return items
            finally:
                if mgr is not None:
                    resolve_audit.participants = mgr._participants
        return items

    # ----- resolver include/exclude filtering -----

    def _filter_configs(self, configs: list) -> list:
        """Apply resolver include/exclude glob filters."""
        include = self.resolver_config.get("include")
        exclude = self.resolver_config.get("exclude")
        if not include and not exclude:
            return configs
        folder = self.path.strip("/")
        result = []
        for cfg in configs:
            relative = config_path_relative_to_folder(cfg.path, folder)
            if include and not any(match_resolver_glob(pat, relative) for pat in include):
                continue
            if exclude and any(match_resolver_glob(pat, relative) for pat in exclude):
                continue
            result.append(cfg)
        return result

    # ----- mark-stable -----

    def _promote_stable_tags(self, promotions: list[tuple[str, int]]) -> None:
        with transaction.atomic():
            for config_path, version in promotions:
                TreeManager(
                    self.namespace,
                    config_path,
                    auth=self.auth,
                ).promote_stable_tag(version)

    # ----- naming -----

    @staticmethod
    def _final_name(
        own_name: str,
        config_path: str,
        folder_base: str | None,
        mgr: ResolvePipelineManager,
    ) -> str:
        """Apply folder-resolution naming rules from the design."""
        if folder_base is None:
            if "/" in own_name:
                return own_name.split("/")[-1]
            return own_name

        relative = config_path
        if folder_base:
            prefix = folder_base + "/"
            if config_path.startswith(prefix):
                relative = config_path[len(prefix) :]
        rel_parts = relative.split("/")

        if own_name == mgr.config_obj.name:
            return relative

        if "/" in own_name:
            return own_name

        rel_parts[-1] = own_name
        return "/".join(rel_parts)

    @staticmethod
    def _apply_folder_naming(
        own_name: str,
        config_path: str,
        folder_base: str | None,
    ) -> str:
        """Folder naming for cache-hit outputs (no pipeline mgr available)."""
        if folder_base is None:
            if "/" in own_name:
                return own_name.split("/")[-1]
            return own_name
        relative = config_path
        if folder_base:
            prefix = folder_base + "/"
            if config_path.startswith(prefix):
                relative = config_path[len(prefix) :]
        config_basename = config_path.split("/")[-1]
        if own_name == config_basename:
            return relative
        if "/" in own_name:
            return own_name
        parts = relative.split("/")
        parts[-1] = own_name
        return "/".join(parts)

    # ----- response assembly -----

    def _build_download_url(self, request_path: str, token: str) -> str:
        return f"{self.base_url}/api/v1/ns/{self.namespace.name}/~resolve/{request_path}/~download/{token}"

    def _effective_resolver_payload(self) -> dict[str, Any] | None:
        """Expose effective resolver configuration for resolver-authenticated calls."""
        if self.resolver_mgr is None:
            return None
        rc = self.resolver_config
        payload: dict[str, Any] = {
            "hooks": {field: rc[field] for field in _RESOLVER_HOOK_FIELDS if rc.get(field)},
        }
        cast_block = rc.get("cast")
        if cast_block:
            payload["cast"] = cast_block.get("format") if isinstance(cast_block, dict) else cast_block
        parameters = rc.get("parameters")
        if parameters:
            payload["parameters"] = parameters
        return payload

    @staticmethod
    def _wrap_response(
        items: list[dict[str, Any]],
        *,
        trace_only: bool,
        root: dict[str, Any] | None,
        resolver: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_items = [{k: v for k, v in it.items() if k != "_cache"} for it in items]
        payload: dict[str, Any] = {"items": clean_items, "length": len(clean_items)}
        if trace_only:
            payload["trace_only"] = True
            if root is not None:
                payload["root"] = root
        if resolver is not None:
            payload["resolver"] = resolver
        return payload

    @staticmethod
    def _cache_status(items: list[dict[str, Any]]) -> str:
        """Return cache tier for the response.

        ``'hit'``  — all items served from Layer 2 (no pipeline, no cast).
        ``'cast'`` — all items served from Layer 1 (no pipeline, re-cast).
        ``'miss'`` — any item required a full pipeline run.
        """
        if not items:
            return "miss"
        statuses = {it.get("_cache") for it in items}
        if statuses == {"hit"}:
            return "hit"
        if "miss" not in statuses and "cast" in statuses:
            return "cast"
        return "miss"
