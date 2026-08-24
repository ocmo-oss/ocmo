"""Credential providers and token cache for the OCMO SDK.

Three supported auth modes:
  - oidc          — OAuth2 client_credentials (primary) or password grant (local Dex)
  - resolver-token — X-Ocmo-Resolver-Token header (secondary)
  - bearer        — pre-obtained bearer, no refresh

Token cache (OIDC only): files under OCMO_CACHE_DIR, keyed by
(issuer, client_id, audience, scope, grant_type, optional auth profile), mode 0600, directory 0700.
Client secrets are NEVER written to disk.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import stat
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from .errors import OcmoAuthError, OcmoConfigError

if TYPE_CHECKING:
    from .config import OcmoConfig

logger = logging.getLogger("ocmo")

_RESOLVER_TOKEN_ONLY_PATHS = frozenset({"~resolve", "~resolve-parameters", "~download", "whoami", "can-i"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_makedirs(directory: Path) -> None:
    """Create directory with mode 0700, refuse group/world-writable parents."""
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    # Verify no world/group write bits on the directory itself
    mode = directory.stat().st_mode
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise OcmoConfigError(
            f"Token cache directory {directory} is group- or world-writable; "
            "refusing to use it. Fix permissions (chmod 700) first."
        )


def _cache_key(
    issuer: str,
    client_id: str,
    audience: str | None,
    scope: str,
    grant_type: str,
    username: str | None = None,
    auth_profile: str | None = None,
) -> str:
    raw = (
        f"{issuer}\x00{client_id}\x00{audience or ''}\x00{scope}\x00"
        f"{grant_type}\x00{username or ''}\x00{auth_profile or ''}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _write_cache(directory: Path, key: str, data: dict[str, object]) -> None:
    try:
        _safe_makedirs(directory)
        path = directory / key
        path.write_text(json.dumps(data))
        path.chmod(0o600)
    except OSError as exc:
        logger.debug("Failed to write token cache: %s", exc)


def _read_cache(directory: Path, key: str) -> dict[str, object] | None:
    path = directory / key
    try:
        mode = path.stat().st_mode
        if mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
            logger.warning("Token cache file %s has insecure permissions; ignoring.", path)
            return None
        result: dict[str, object] = json.loads(path.read_text())
        return result
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------


class _OIDCTokenCache:
    """In-memory + on-disk cache for OIDC access tokens."""

    def __init__(
        self,
        cache_dir: Path,
        issuer: str,
        client_id: str,
        audience: str | None,
        scope: str,
        grant_type: str,
        username: str | None = None,
        auth_profile: str | None = None,
    ) -> None:
        self._dir = cache_dir
        self._key = _cache_key(
            issuer,
            client_id,
            audience,
            scope,
            grant_type,
            username,
            auth_profile,
        )
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get(self) -> str | None:
        now = time.time()
        if self._token and now < self._expires_at:
            return self._token
        # Try disk cache
        cached = _read_cache(self._dir, self._key)
        if cached and now < float(cached.get("expires_at", 0)):  # type: ignore[arg-type]
            self._token = str(cached["access_token"])
            self._expires_at = float(cached["expires_at"])  # type: ignore[arg-type]
            return self._token
        return None

    def set(self, token: str, expires_in: int) -> None:
        # Proactive refresh at 80% of lifetime
        self._token = token
        self._expires_at = time.time() + expires_in * 0.8
        _write_cache(
            self._dir,
            self._key,
            {
                "access_token": token,
                "expires_at": self._expires_at,
            },
        )

    def invalidate(self) -> None:
        """Clear in-memory and on-disk cache, forcing a fresh fetch on next get()."""
        self._token = None
        self._expires_at = 0.0
        try:
            (self._dir / self._key).unlink(missing_ok=True)
        except OSError:
            pass


def _fetch_oidc_discovery(issuer: str) -> dict[str, object]:
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=10)
        resp.raise_for_status()
        result: dict[str, object] = resp.json()
        return result
    except httpx.HTTPError as exc:
        raise OcmoAuthError(f"Failed to fetch OIDC discovery document from {url}: {exc}") from exc


def _fetch_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    scope: str,
    audience: str | None,
    *,
    grant_type: str = "client_credentials",
    username: str | None = None,
    password: str | None = None,
) -> tuple[str, int]:
    """Acquire an access token via client_credentials or password grant."""
    data: dict[str, str] = {
        "grant_type": grant_type,
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
    }
    if grant_type == "password":
        if not username or not password:
            raise OcmoConfigError(
                "OIDC password grant requires OCMO_OIDC_USERNAME and " "OCMO_OIDC_PASSWORD or OCMO_OIDC_PASSWORD_FILE."
            )
        data["username"] = username
        data["password"] = password
    if audience:
        data["audience"] = audience

    try:
        resp = httpx.post(
            token_url,
            data=data,
            timeout=15,
            follow_redirects=False,
        )
        if resp.status_code != 200:
            # Do NOT include client_secret in error messages
            raise OcmoAuthError(
                f"Token endpoint returned {resp.status_code}. " f"Check OCMO_CLIENT_ID and OCMO_CLIENT_SECRET."
            )
        payload = resp.json()
    except httpx.HTTPError as exc:
        raise OcmoAuthError(f"Token endpoint request failed: {exc}") from exc

    access_token = payload.get("access_token")
    if not access_token:
        raise OcmoAuthError("Token endpoint response missing 'access_token'.")
    expires_in = int(payload.get("expires_in", 3600))
    return access_token, expires_in


# ---------------------------------------------------------------------------
# Auth providers
# ---------------------------------------------------------------------------


class _OIDCProvider:
    """Obtain and cache OIDC access tokens."""

    def __init__(self, config: OcmoConfig) -> None:
        if not config.client_id:
            raise OcmoConfigError("OIDC auth mode requires OCMO_CLIENT_ID.")
        if config.oidc_grant_type == "password" and (not config.oidc_username or not config.oidc_password):
            raise OcmoConfigError(
                "OIDC password grant requires OCMO_OIDC_USERNAME and " "OCMO_OIDC_PASSWORD or OCMO_OIDC_PASSWORD_FILE."
            )
        self._config = config
        self._client_id = config.client_id
        self._scope = config.oidc_scope
        self._audience = config.oidc_audience
        self._grant_type = config.oidc_grant_type
        self._username = config.oidc_username
        self._password = config.oidc_password
        self._token_url: str | None = config.oidc_token_url
        self._cache = _OIDCTokenCache(
            config.cache_dir,
            config.oidc_issuer or "",
            self._client_id,
            self._audience,
            self._scope,
            self._grant_type,
            self._username,
            config.oidc_cache_profile,
        )
        cached = self._cache.get()
        if not config.client_secret:
            if cached is None:
                raise OcmoConfigError(
                    "OIDC auth mode requires OCMO_CLIENT_SECRET or OCMO_CLIENT_SECRET_FILE "
                    "(or a cached token from 'ocmo auth login')."
                )
            self._client_secret = ""
        else:
            self._client_secret = config.client_secret

    def _resolve_token_url(self, api_version_info: dict[str, Any] | None = None) -> str:
        if self._token_url:
            return self._token_url
        issuer = self._config.oidc_issuer
        if not issuer and api_version_info:
            auth_section = api_version_info.get("auth") or {}
            oidc_section = (auth_section.get("oidc") or {}) if isinstance(auth_section, dict) else {}
            issuer = str(oidc_section.get("issuer") or "") if isinstance(oidc_section, dict) else ""
        if not issuer:
            raise OcmoConfigError("OIDC auth mode requires OCMO_OIDC_ISSUER or a running API at OCMO_SERVER.")
        discovery = _fetch_oidc_discovery(issuer)
        url = discovery.get("token_endpoint")
        if not url:
            raise OcmoConfigError(f"OIDC discovery at {issuer} has no token_endpoint.")
        self._token_url = str(url)
        return self._token_url

    def get_token(self, api_version_info: dict[str, Any] | None = None) -> str:
        cached = self._cache.get()
        if cached:
            return cached
        if not self._client_secret:
            raise OcmoAuthError(
                "Cached OIDC token expired or missing. "
                "Run 'ocmo auth login' again, or set OCMO_CLIENT_SECRET for automatic refresh."
            )
        token_url = self._resolve_token_url(api_version_info)
        token, expires_in = _fetch_token(
            token_url,
            self._client_id,
            self._client_secret,
            self._scope,
            self._audience,
            grant_type=self._grant_type,
            username=self._username,
            password=self._password,
        )
        self._cache.set(token, expires_in)
        return token

    def refresh(self, api_version_info: dict[str, Any] | None = None) -> str:
        """Force token re-acquisition (called on 401)."""
        self._cache.invalidate()
        return self.get_token(api_version_info)

    def inject_headers(self, headers: dict[str, str], api_version_info: dict[str, Any] | None = None) -> None:
        token = self.get_token(api_version_info)
        headers["Authorization"] = f"Bearer {token}"


class _ResolverTokenProvider:
    """Send a resolver token via the X-Ocmo-Resolver-Token header."""

    # Endpoints accessible with a resolver token
    _ALLOWED_PATH_SEGMENTS = frozenset({"~resolve", "~resolve-parameters", "~download", "whoami", "can-i"})

    def __init__(self, token: str) -> None:
        if not token:
            raise OcmoConfigError("resolver-token auth mode requires OCMO_TOKEN.")
        self._token = token

    def inject_headers(self, headers: dict[str, str], path: str = "") -> None:
        headers["X-Ocmo-Resolver-Token"] = self._token

    def check_path_allowed(self, path: str) -> None:
        """Raise if this path cannot be used with a resolver token."""
        segments = set(path.strip("/").split("/"))
        if not segments.intersection(self._ALLOWED_PATH_SEGMENTS):
            raise OcmoAuthError(
                f"Resolver tokens can only be used with resolve and whoami endpoints. "
                f"The path {path!r} requires OIDC authentication."
            )


class _BearerProvider:
    """Pass a pre-obtained bearer token; re-read file on 401."""

    def __init__(self, token: str, token_file: str | None = None) -> None:
        if not token:
            raise OcmoConfigError("bearer auth mode requires OCMO_TOKEN or OCMO_TOKEN_FILE.")
        self._token = token
        self._token_file = token_file

    def inject_headers(self, headers: dict[str, str]) -> None:
        headers["Authorization"] = f"Bearer {self._token}"

    def refresh_from_file(self) -> bool:
        """Re-read token from file after a 401. Returns True if token changed."""
        if not self._token_file:
            return False
        try:
            new_token = Path(self._token_file).read_text().strip()
            if new_token != self._token:
                self._token = new_token
                return True
        except OSError:
            pass
        return False


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

CredentialProvider = _OIDCProvider | _ResolverTokenProvider | _BearerProvider


def build_provider(config: OcmoConfig) -> CredentialProvider | None:
    """Construct the appropriate credential provider from config."""
    mode = config.auth_mode
    if mode == "oidc":
        return _OIDCProvider(config)
    if mode == "resolver-token":
        token = config.token
        if not token:
            raise OcmoConfigError("resolver-token auth mode requires OCMO_TOKEN or OCMO_TOKEN_FILE.")
        return _ResolverTokenProvider(token)
    if mode == "bearer":
        token = config.token
        if not token:
            raise OcmoConfigError("bearer auth mode requires OCMO_TOKEN or OCMO_TOKEN_FILE.")
        # We need token_file for re-read on 401; store on config
        token_file = os.environ.get("OCMO_TOKEN_FILE")
        return _BearerProvider(token, token_file)
    return None  # "none" mode


def oidc_token_cache(config: OcmoConfig) -> _OIDCTokenCache:
    """Return the on-disk OIDC token cache for *config*."""
    if not config.client_id:
        raise OcmoConfigError("OIDC cache requires OCMO_CLIENT_ID.")
    return _OIDCTokenCache(
        config.cache_dir,
        config.oidc_issuer or "",
        config.client_id,
        config.oidc_audience,
        config.oidc_scope,
        config.oidc_grant_type,
        config.oidc_username,
        config.oidc_cache_profile,
    )


def store_oidc_access_token(config: OcmoConfig, access_token: str, expires_in: int) -> None:
    """Persist an OIDC access token in the SDK token cache."""
    oidc_token_cache(config).set(access_token, expires_in)


def invalidate_oidc_token_cache(config: OcmoConfig) -> bool:
    """Remove the cached OIDC token for *config*. Returns True if a file was removed."""
    if not config.client_id:
        return False
    cache = oidc_token_cache(config)
    had = cache.get() is not None or (config.cache_dir / cache._key).exists()
    cache.invalidate()
    return had


def clear_oidc_token_cache_dir(cache_dir: Path) -> int:
    """Remove all SDK OIDC cache entries under *cache_dir*. Returns count removed."""
    removed = 0
    if not cache_dir.is_dir():
        return 0
    for path in cache_dir.iterdir():
        if path.is_file() and len(path.name) == 64 and all(c in "0123456789abcdef" for c in path.name):
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def fetch_oidc_discovery(issuer: str) -> dict[str, object]:
    """Fetch the OIDC provider discovery document."""
    return _fetch_oidc_discovery(issuer)


def oidc_cache_status(config: OcmoConfig) -> dict[str, object]:
    """Return whether an OIDC access token is cached for *config*."""
    if not config.client_id:
        return {"cached": False}
    cache = oidc_token_cache(config)
    path = config.cache_dir / cache._key
    if not path.exists():
        return {"cached": False}
    data = _read_cache(config.cache_dir, cache._key)
    if not data:
        return {"cached": False}
    return {
        "cached": True,
        "expires_at": data.get("expires_at"),
    }
