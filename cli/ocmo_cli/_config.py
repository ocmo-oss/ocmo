"""Local CLI configuration file — kubeconfig-shaped YAML.

Precedence (highest first):
  command flag > OCMO_* env var > current context in config file > built-in default.

File lives at $OCMO_CONFIG or $XDG_CONFIG_HOME/ocmo/config.yaml (default).
Created 0600 in a 0700 directory. Refusing to read world-readable files that
contain inline credentials.
"""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _config_path() -> Path:
    env = os.environ.get("OCMO_CONFIG")
    if env:
        return Path(env)
    xdg = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(xdg) / "ocmo" / "config.yaml"


def format_config_path_note() -> str:
    """Human-readable config file path for help text and command output."""
    path = _config_path()
    note = "" if path.exists() else " (not created yet)"
    return f"Config file: {path}{note}"


@dataclass
class AuthEntry:
    mode: str = "oidc"
    issuer: str = ""
    client_id: str = ""
    client_secret: str = ""
    client_secret_file: str = ""
    token: str = ""
    token_file: str = ""

    def has_inline_secret(self) -> bool:
        return bool(self.client_secret or self.token)


@dataclass
class Context:
    server: str = ""
    namespace: str = ""
    auth: str = ""
    token_file: str = ""


@dataclass
class CliConfig:
    current_context: str = ""
    contexts: dict[str, Context] = field(default_factory=dict)
    auths: dict[str, AuthEntry] = field(default_factory=dict)

    def active_context(self) -> Context | None:
        name = os.environ.get("OCMO_CONTEXT") or self.current_context
        return self.contexts.get(name)

    def server(self) -> str:
        env = os.environ.get("OCMO_SERVER")
        if env:
            return env
        ctx = self.active_context()
        return ctx.server if ctx else ""

    def namespace(self) -> str:
        env = os.environ.get("OCMO_NAMESPACE")
        if env:
            return env
        ctx = self.active_context()
        return ctx.namespace if ctx else ""


def load_config() -> CliConfig:
    """Load the config file if it exists; return an empty config otherwise."""
    import yaml  # deferred

    path = _config_path()
    if not path.exists():
        return CliConfig()

    _check_permissions(path)

    with path.open() as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    cfg = CliConfig(current_context=raw.get("current-context", ""))

    for name, ctx_raw in (raw.get("contexts") or {}).items():
        cfg.contexts[name] = Context(
            server=ctx_raw.get("server", ""),
            namespace=ctx_raw.get("namespace", ""),
            auth=ctx_raw.get("auth", ""),
            token_file=ctx_raw.get("token-file", ""),
        )

    for name, auth_raw in (raw.get("auths") or {}).items():
        entry = AuthEntry(
            mode=auth_raw.get("mode", "oidc"),
            issuer=auth_raw.get("issuer", ""),
            client_id=auth_raw.get("client_id", ""),
            client_secret=auth_raw.get("client_secret", ""),
            client_secret_file=auth_raw.get("client_secret_file", ""),
            token=auth_raw.get("token", ""),
            token_file=auth_raw.get("token_file", ""),
        )
        if entry.has_inline_secret():
            print(
                f"Warning: auth '{name}' contains an inline credential. "
                "Consider using the *_file variant, a keyring, or an environment variable.",
                file=sys.stderr,
            )
        cfg.auths[name] = entry

    return cfg


def save_config(cfg: CliConfig) -> None:
    """Write config to disk with 0600/0700 permissions."""
    import yaml  # deferred

    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)

    raw: dict[str, Any] = {}
    if cfg.current_context:
        raw["current-context"] = cfg.current_context
    if cfg.contexts:
        raw["contexts"] = {name: _ctx_to_dict(ctx) for name, ctx in cfg.contexts.items()}
    if cfg.auths:
        raw["auths"] = {name: _auth_to_dict(auth) for name, auth in cfg.auths.items()}

    with path.open("w") as f:
        yaml.safe_dump(raw, f, default_flow_style=False)
    os.chmod(path, 0o600)


def _ctx_to_dict(ctx: Context) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if ctx.server:
        d["server"] = ctx.server
    if ctx.namespace:
        d["namespace"] = ctx.namespace
    if ctx.auth:
        d["auth"] = ctx.auth
    if ctx.token_file:
        d["token-file"] = ctx.token_file
    return d


def _auth_to_dict(auth: AuthEntry) -> dict[str, Any]:
    d: dict[str, Any] = {"mode": auth.mode}
    for k in ("issuer", "client_id", "client_secret", "client_secret_file", "token", "token_file"):
        v = getattr(auth, k)
        if v:
            d[k] = v
    return d


def _check_permissions(path: Path) -> None:
    """Refuse to read a world-readable config that contains credentials."""
    try:
        mode = path.stat().st_mode
    except OSError:
        return
    if mode & stat.S_IROTH:
        # World-readable: read but warn unless no credentials present
        print(
            f"Warning: config file {path} is world-readable. "
            "This is a security risk if it contains credentials. "
            "Run: chmod 600 " + str(path),
            file=sys.stderr,
        )
