"""Client factory — builds an OcmoClient from CLI context.

All SDK imports are deferred so that --help and startup remain fast.
Supports all OCMO_* environment variables documented in sdk/ocmo/config.py.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ocmo import NamespaceView, OcmoClient
    from ocmo.config import OcmoConfig

    from ._config import CliConfig, Context

from ._auth_resolve import (
    apply_resolved_oidc_to_kwargs,
    resolve_oidc_settings,
)


class OcmoCtx:
    """CLI runtime context threaded through click.Context.obj."""

    def __init__(
        self,
        *,
        namespace: str | None,
        output: str | None,
        dry_run: bool,
        verbose: bool,
        quiet: bool,
        yes: bool,
        skip_version_check: bool,
        no_color: bool,
    ) -> None:
        self.namespace = namespace
        self.output = output
        self.dry_run = dry_run
        self.verbose = verbose
        self.quiet = quiet
        self.yes = yes
        self.skip_version_check = skip_version_check
        self.no_color = no_color
        self._client: OcmoClient | None = None

    def client(self) -> OcmoClient:
        """Return a cached OcmoClient built from the CLI context and env."""
        if self._client is None:
            self._client = _build_client(
                skip_version_check=self.skip_version_check,
                verbose=self.verbose,
            )
        return self._client

    def ns(self, namespace: str | None = None) -> NamespaceView:
        """Return a NamespaceView for the effective namespace."""
        ns = namespace or self.namespace or _resolve_namespace()
        if not ns:
            _abort_missing_namespace()
        return self.client().ns(ns)

    def require_namespace(self, namespace: str | None = None) -> str:
        ns = namespace or self.namespace or _resolve_namespace()
        if not ns:
            _abort_missing_namespace()
        assert ns is not None
        return ns

    def namespace_view(self, namespace: str | None = None) -> NamespaceView:
        """Return a NamespaceView for the effective namespace."""
        return self.ns(self.require_namespace(namespace))


def _resolve_namespace() -> str | None:
    # 1. Environment variable (SDK layer handles this too, but check here for CLI error message)
    env = os.environ.get("OCMO_NAMESPACE")
    if env:
        return env
    # 2. Config file context
    try:
        from ._config import load_config  # deferred

        cfg = load_config()
        return cfg.namespace() or None
    except Exception:
        return None


def _fetch_oidc_from_server(server: str | None) -> dict[str, str]:
    """Return public OIDC hints from the API ``/api/version`` endpoint."""
    if not server:
        return {}
    try:
        import httpx  # deferred

        url = server.rstrip("/") + "/api/version"
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
        oidc = (resp.json().get("auth") or {}).get("oidc") or {}
        return {k: str(v) for k, v in oidc.items() if v is not None}
    except Exception:
        return {}


def _fetch_oidc_scopes_from_server(server: str | None) -> str | None:
    """Return OIDC scopes advertised by the API (unauthenticated /version)."""
    scopes = _fetch_oidc_from_server(server).get("scopes")
    return scopes if scopes else None


def _build_client(*, skip_version_check: bool, verbose: bool) -> OcmoClient:
    """Build an OcmoClient with all config options from env + CLI config file."""
    from ocmo import OcmoClient  # deferred

    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    return OcmoClient(config=build_ocmo_config(skip_version_check=skip_version_check))


def _uses_token_auth(cfg: CliConfig | None = None, ctx: Context | None = None) -> bool:
    """True when auth should use OCMO_TOKEN / token file (resolver or bearer)."""
    if os.environ.get("OCMO_AUTH_MODE") in ("resolver-token", "bearer"):
        return True
    if os.environ.get("OCMO_TOKEN") or os.environ.get("OCMO_TOKEN_FILE"):
        return True
    try:
        if cfg is None:
            cfg = _load_cli_config()
        if ctx is None:
            ctx_name = _resolve_context_name(cfg, None)
            ctx = cfg.contexts.get(ctx_name) if ctx_name else cfg.active_context()
        if ctx is None:
            return False
        if ctx.token_file:
            return True
        if not ctx.auth:
            return False
        entry = cfg.auths.get(ctx.auth)
        return bool(entry and (entry.token or entry.token_file))
    except Exception:
        return False


def build_ocmo_config(
    *,
    skip_version_check: bool = False,
    context_name: str | None = None,
    validate_auth: bool = True,
) -> OcmoConfig:
    """Build OcmoConfig from environment variables and the CLI config file."""
    from ocmo.config import OcmoConfig  # deferred

    cfg = _load_cli_config()
    ctx_name = _resolve_context_name(cfg, context_name)
    ctx = cfg.contexts.get(ctx_name) if ctx_name else None

    server = os.environ.get("OCMO_SERVER") or (ctx.server if ctx else None) or cfg.server()
    if server:
        os.environ.setdefault("OCMO_SERVER", server)

    file_auth = _auth_kwargs_from_context(cfg, ctx)
    token_auth = _uses_token_auth(cfg, ctx)
    auth_profile = ctx.auth if ctx and ctx.auth else None

    if token_auth:
        file_auth = {k: v for k, v in file_auth.items() if k in ("token", "token_file")}
    else:
        oidc_hints = _fetch_oidc_from_server(server) if server else {}
        entry = cfg.auths.get(ctx.auth) if ctx and ctx.auth else None
        if entry and entry.mode == "oidc" and not (entry.token or entry.token_file):
            resolved = resolve_oidc_settings(
                server=server,
                entry=entry,
                fetch_server_oidc=_fetch_oidc_from_server,
            )
            apply_resolved_oidc_to_kwargs(file_auth, resolved)
        if not os.environ.get("OCMO_OIDC_SCOPE") and file_auth.get("oidc_scope") is None:
            scopes = oidc_hints.get("scopes")
            if scopes:
                file_auth["oidc_scope"] = scopes

    auth_kwargs = {k: v for k, v in file_auth.items() if v is not None}
    sdk_cfg = OcmoConfig.from_env(
        skip_version_check=skip_version_check if skip_version_check else None,
        oidc_cache_profile=auth_profile,
        oidc_issuer=auth_kwargs.get("oidc_issuer"),
        client_id=auth_kwargs.get("client_id"),
        client_secret=auth_kwargs.get("client_secret"),
        client_secret_file=auth_kwargs.get("client_secret_file"),
        token=auth_kwargs.get("token"),
        token_file=auth_kwargs.get("token_file"),
        oidc_scope=auth_kwargs.get("oidc_scope"),
    )
    if validate_auth:
        _validate_cli_auth(cfg, ctx, sdk_cfg)
    return sdk_cfg


def _load_cli_config() -> CliConfig:
    from ._config import load_config

    return load_config()


def _resolve_context_name(cfg: CliConfig, explicit: str | None = None) -> str | None:
    return explicit or os.environ.get("OCMO_CONTEXT") or cfg.current_context or None


def _validate_cli_auth(cfg: CliConfig, ctx: Context | None, sdk_cfg: OcmoConfig) -> None:
    """Require explicit auth configuration before API calls."""
    from ocmo.errors import OcmoConfigError  # deferred

    if sdk_cfg.auth_mode in ("resolver-token", "bearer"):
        return
    if sdk_cfg.token:
        return
    if ctx and ctx.token_file:
        return

    env_oidc = bool(os.environ.get("OCMO_CLIENT_ID") and os.environ.get("OCMO_OIDC_ISSUER"))
    if env_oidc:
        return

    auth_name = ctx.auth if ctx else None
    if not auth_name:
        raise OcmoConfigError(_missing_auth_message(cfg, ctx, reason="no_auth_reference"))

    entry = cfg.auths.get(auth_name)
    if entry is None:
        raise OcmoConfigError(_missing_auth_message(cfg, ctx, reason="missing_auth_entry"))

    if entry.token or entry.token_file:
        return

    if entry.mode != "oidc":
        raise OcmoConfigError(f"auths.{auth_name} uses unsupported mode {entry.mode!r}; expected 'oidc'.")

    if not sdk_cfg.client_id or not sdk_cfg.oidc_issuer:
        raise OcmoConfigError(_missing_auth_message(cfg, ctx, reason="incomplete_auth_entry"))


def _missing_auth_message(cfg: CliConfig, ctx: Context | None, *, reason: str) -> str:
    from ._config import _config_path

    config_path = _config_path()
    ctx_name = ctx and _resolve_context_name(cfg, None)
    auth_name = ctx.auth if ctx else None
    lines = [
        "Authentication is not configured for the active context.",
        "",
        "Define an auths: entry in the config file and reference it from the context:",
        "  auths:",
        f"    {auth_name or 'my-oidc'}:",
        "      mode: oidc",
        "      # issuer / client_id optional — env, /api/version, or:",
        "      # issuer: https://sso.example.com",
        "      # client_id: ocmo-cli",
        "  contexts:",
        f"    {ctx_name or 'default'}:",
        f"      auth: {auth_name or 'my-oidc'}",
        "",
        "Or set environment variables:",
        "  OCMO_OIDC_ISSUER, OCMO_CLIENT_ID",
        "  OCMO_CLIENT_SECRET (when required)",
        "",
        f"Config file: {config_path}",
    ]
    if reason == "missing_auth_entry" and auth_name:
        lines.insert(2, f"Context {ctx_name!r} references auth {auth_name!r}, but auths.{auth_name} is missing.")
    elif reason == "no_auth_reference" and ctx_name:
        lines.insert(2, f"Context {ctx_name!r} has no auth: field.")
    elif reason == "incomplete_auth_entry" and auth_name:
        lines.insert(
            2,
            f"Could not resolve OIDC issuer and client_id for auths.{auth_name} "
            "(set them in the config, OCMO_OIDC_ISSUER/OCMO_CLIENT_ID, or ensure "
            "the context server exposes them via /api/version).",
        )
    return "\n".join(lines)


def _auth_kwargs_from_context(cfg: CliConfig, ctx: Context | None) -> dict[str, str | None]:
    """Merge auth settings from a specific context when env is unset."""
    if not ctx:
        return {}

    kwargs: dict[str, str | None] = {}

    if ctx.token_file and not os.environ.get("OCMO_TOKEN") and not os.environ.get("OCMO_TOKEN_FILE"):
        kwargs["token_file"] = ctx.token_file

    auth_name = ctx.auth
    if not auth_name:
        return kwargs

    entry = cfg.auths.get(auth_name)
    if not entry:
        return kwargs

    def _set(env_var: str, config_key: str, value: str | None) -> None:
        if value and not os.environ.get(env_var):
            kwargs[config_key] = value

    _set("OCMO_OIDC_ISSUER", "oidc_issuer", entry.issuer or None)
    _set("OCMO_CLIENT_ID", "client_id", entry.client_id or None)
    _set("OCMO_CLIENT_SECRET", "client_secret", entry.client_secret or None)
    _set("OCMO_CLIENT_SECRET_FILE", "client_secret_file", entry.client_secret_file or None)
    _set("OCMO_TOKEN", "token", entry.token or None)
    _set("OCMO_TOKEN_FILE", "token_file", entry.token_file or None)

    return kwargs


def _auth_kwargs_from_config() -> dict[str, str | None]:
    """Merge auth settings from the active CLI context when env is unset."""
    try:
        cfg = _load_cli_config()
    except Exception:
        return {}
    ctx_name = _resolve_context_name(cfg, None)
    ctx = cfg.contexts.get(ctx_name) if ctx_name else cfg.active_context()
    return _auth_kwargs_from_context(cfg, ctx)


def _server_from_config() -> str | None:
    """Read server URL from the config file context."""
    try:
        from ._config import load_config

        cfg = load_config()
        return cfg.server() or None
    except Exception:
        return None


def _abort_missing_namespace() -> None:
    print(
        "Error: namespace is required. Specify it via:\n"
        "  -n / --namespace flag\n"
        "  OCMO_NAMESPACE environment variable\n"
        "  current context in the config file (ocmo config set namespace <ns>)",
        file=sys.stderr,
    )
    raise SystemExit(2)
