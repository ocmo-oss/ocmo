"""Resolve OIDC settings from config entries, environment, and API hints."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from ._config import AuthEntry, CliConfig


@dataclass(frozen=True)
class ResolvedOidc:
    issuer: str
    client_id: str
    client_secret: str


def ensure_auth_entry(cfg: CliConfig, name: str, *, mode: str = "oidc") -> AuthEntry:
    """Return an auth block, creating ``mode``-only stub when missing."""
    entry = cfg.auths.get(name)
    if entry is None:
        entry = AuthEntry(mode=mode)
        cfg.auths[name] = entry
    return entry


def resolve_oidc_settings(
    *,
    server: str | None,
    entry: AuthEntry | None,
    fetch_server_oidc: Callable[[str | None], dict[str, str]],
) -> ResolvedOidc:
    """Merge OIDC client settings: env → config entry → ``/api/version`` hints."""
    hints = fetch_server_oidc(server) if server else {}

    issuer = os.environ.get("OCMO_OIDC_ISSUER") or (entry.issuer if entry else "") or hints.get("issuer", "")
    client_id = os.environ.get("OCMO_CLIENT_ID") or (entry.client_id if entry else "") or hints.get("client_id", "")
    client_secret = os.environ.get("OCMO_CLIENT_SECRET") or (entry.client_secret if entry else "") or ""
    return ResolvedOidc(
        issuer=issuer or "",
        client_id=client_id or "",
        client_secret=client_secret or "",
    )


def apply_resolved_oidc_to_kwargs(
    kwargs: dict[str, str | None],
    resolved: ResolvedOidc,
) -> None:
    """Fill SDK kwargs for unset env-backed OIDC fields."""
    if resolved.issuer and not os.environ.get("OCMO_OIDC_ISSUER") and not kwargs.get("oidc_issuer"):
        kwargs["oidc_issuer"] = resolved.issuer
    if resolved.client_id and not os.environ.get("OCMO_CLIENT_ID") and not kwargs.get("client_id"):
        kwargs["client_id"] = resolved.client_id
    if resolved.client_secret and not os.environ.get("OCMO_CLIENT_SECRET") and not kwargs.get("client_secret"):
        kwargs["client_secret"] = resolved.client_secret


def auth_entry_from_resolved(resolved: ResolvedOidc) -> AuthEntry:
    return AuthEntry(
        mode="oidc",
        issuer=resolved.issuer,
        client_id=resolved.client_id,
        client_secret=resolved.client_secret,
    )
