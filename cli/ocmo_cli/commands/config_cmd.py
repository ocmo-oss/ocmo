"""ocmo config — manage the local configuration file and contexts."""

from __future__ import annotations

from typing import Any

import click

from .._auth_resolve import ensure_auth_entry
from .._click_groups import ConfigPathHelpGroup
from .._config import (
    Context,
    format_config_path_note,
    load_config,
    save_config,
)
from .._output import err

_SETTABLE_CONTEXT_KEYS = ("server", "namespace", "token-file", "auth")

_CONFIG_HELP = """\
Manage local CLI configuration (server, contexts, auth).
"""


@click.group("config", cls=ConfigPathHelpGroup, help=_CONFIG_HELP)
def config_group() -> None:
    """Manage local CLI configuration (server, contexts, auth)."""


@config_group.command("view")
@click.option(
    "--show-secrets", is_flag=True, default=False, help="Show credential fields (CAUTION: may expose secrets)."
)
def view_cmd(show_secrets: bool) -> None:
    """Print the current configuration file, redacting credentials by default."""
    import yaml  # deferred

    cfg = load_config()
    raw: dict[str, Any] = {
        "current-context": cfg.current_context,
        "contexts": {},
        "auths": {},
    }
    for name, ctx in cfg.contexts.items():
        raw["contexts"][name] = {
            "server": ctx.server,
            "namespace": ctx.namespace,
            "auth": ctx.auth,
        }
        if ctx.token_file:
            raw["contexts"][name]["token-file"] = ctx.token_file

    for name, auth in cfg.auths.items():
        entry: dict[str, Any] = {"mode": auth.mode}
        if auth.issuer:
            entry["issuer"] = auth.issuer
        if auth.client_id:
            entry["client_id"] = auth.client_id
        if show_secrets:
            if auth.client_secret:
                entry["client_secret"] = auth.client_secret
            if auth.token:
                entry["token"] = auth.token
        else:
            if auth.client_secret:
                entry["client_secret"] = "***REDACTED***"
            if auth.token:
                entry["token"] = "***REDACTED***"
        if auth.client_secret_file:
            entry["client_secret_file"] = auth.client_secret_file
        if auth.token_file:
            entry["token_file"] = auth.token_file
        raw["auths"][name] = entry

    print(yaml.safe_dump(raw, default_flow_style=False), end="")
    print(f"\n# {format_config_path_note()}")


@config_group.command("get-contexts")
def get_contexts_cmd() -> None:
    """List available contexts."""
    cfg = load_config()
    if not cfg.contexts:
        print("No contexts configured.")
        return
    current = cfg.current_context
    for name, ctx in cfg.contexts.items():
        marker = "*" if name == current else " "
        print(f"{marker} {name:20s}  {ctx.server:40s}  {ctx.namespace}")


@config_group.command("current-context")
def current_context_cmd() -> None:
    """Print the name of the current context."""
    cfg = load_config()
    print(cfg.current_context or "(none)")


@config_group.command("current-ns")
def current_ns_cmd() -> None:
    """Print the effective namespace (OCMO_NAMESPACE or current context)."""
    cfg = load_config()
    print(cfg.namespace() or "(none)")


@config_group.command("use-context")
@click.argument("name")
def use_context_cmd(name: str) -> None:
    """Set the current context."""
    cfg = load_config()
    if name not in cfg.contexts:
        available = list(cfg.contexts)
        err(
            f"Context {name!r} not found. "
            + (f"Available: {', '.join(available)}" if available else "No contexts configured.")
        )
        raise SystemExit(1)
    cfg.current_context = name
    save_config(cfg)
    print(f"Switched to context {name!r}.")


@config_group.command("set-context")
@click.argument("name")
@click.option("--server", default=None)
@click.option("--namespace", default=None)
@click.option("--auth", default=None)
@click.option("--token-file", default=None)
def set_context_cmd(
    name: str,
    server: str | None,
    namespace: str | None,
    auth: str | None,
    token_file: str | None,
) -> None:
    """Create or update a named context."""
    cfg = load_config()
    ctx = cfg.contexts.get(name, Context())
    if server:
        ctx.server = server
    if namespace:
        ctx.namespace = namespace
    if auth:
        ctx.auth = auth
        ensure_auth_entry(cfg, auth)
    if token_file:
        ctx.token_file = token_file
    cfg.contexts[name] = ctx
    save_config(cfg)
    print(f"Context {name!r} updated.")


@config_group.command("set-auth")
@click.argument("name")
@click.option("--mode", default=None, help="Auth mode (default: oidc).")
@click.option("--issuer", default=None, help="OIDC issuer URL.")
@click.option("--client-id", default=None, help="OIDC client ID.")
@click.option("--client-secret", default=None, help="OIDC client secret (inline).")
@click.option("--client-secret-file", default=None, help="Path to OIDC client secret file.")
@click.option("--token", default=None, help="Bearer or resolver token (inline).")
@click.option("--token-file", default=None, help="Path to bearer/resolver token file.")
def set_auth_cmd(
    name: str,
    mode: str | None,
    issuer: str | None,
    client_id: str | None,
    client_secret: str | None,
    client_secret_file: str | None,
    token: str | None,
    token_file: str | None,
) -> None:
    """Create or update a named auth block.

    ``issuer`` and ``client_id`` are optional in the config file; at runtime they
    are resolved from environment variables or ``GET /api/version`` for the context
    server when unset.
    """
    cfg = load_config()
    entry = ensure_auth_entry(cfg, name, mode=mode or "oidc")
    if mode:
        entry.mode = mode
    if issuer is not None:
        entry.issuer = issuer
    if client_id is not None:
        entry.client_id = client_id
    if client_secret is not None:
        entry.client_secret = client_secret
    if client_secret_file is not None:
        entry.client_secret_file = client_secret_file
    if token is not None:
        entry.token = token
    if token_file is not None:
        entry.token_file = token_file
    cfg.auths[name] = entry
    save_config(cfg)
    print(f"Auth {name!r} updated.")


@config_group.command("set")
@click.argument("key", type=click.Choice(list(_SETTABLE_CONTEXT_KEYS)))
@click.argument("value")
def set_cmd(key: str, value: str) -> None:
    """Set a field in the current context.

    \b
    Supported keys:
      server       — API base URL
      namespace    — default namespace for -n
      token-file   — path to a resolver or bearer token file
      auth         — name of an auths: entry to attach
    """
    cfg = load_config()
    if not cfg.current_context:
        # Create a default context
        cfg.current_context = "default"
        if "default" not in cfg.contexts:
            cfg.contexts["default"] = Context()

    ctx_name = cfg.current_context
    ctx = cfg.contexts.get(ctx_name, Context())

    if key == "server":
        ctx.server = value
    elif key == "namespace":
        ctx.namespace = value
    elif key == "token-file":
        ctx.token_file = value
    elif key == "auth":
        ctx.auth = value
        ensure_auth_entry(cfg, value)

    cfg.contexts[ctx_name] = ctx
    save_config(cfg)
    print(f"Set {key} = {value!r} in context {ctx_name!r}.")
