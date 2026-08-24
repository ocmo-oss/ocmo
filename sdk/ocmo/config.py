"""Configuration resolution for the OCMO SDK.

Precedence (highest → lowest):
  explicit constructor argument → OCMO_* environment variable → built-in default

Every setting that carries credentials has a ``_FILE`` variant: the file path is
read at client construction time; the content is used as the secret value.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from .errors import OcmoConfigError

# ---------------------------------------------------------------------------
# Server-side variable names that the SDK MUST NOT reuse (§7 namespace collision)
# ---------------------------------------------------------------------------
_SERVER_SIDE_VARS: frozenset[str] = frozenset(
    {
        "OCMO_RESOLVE_CACHE_TTL",
        "OCMO_MASTER_KEY",
        "OCMO_RESOLVE_URL_TTL",
        "OCMO_SECRET_ENCRYPTION_KEY",
        "OCMO_DB_HOST",
        "OCMO_DB_PORT",
        "OCMO_DB_NAME",
        "OCMO_DB_USER",
        "OCMO_DB_PASSWORD",
        "OCMO_SECRET_BACKEND",
        "OCMO_ARTIFACT_BACKEND",
        "OCMO_ARTIFACT_DIR",
        "OCMO_CONFIG_METADATA_KEY",
        "OCMO_OIDC_ISSUER_INTERNAL",
        "OCMO_OIDC_CLIENT_ID",
        "OCMO_OIDC_SCOPES",
        "OCMO_OIDC_AUTHORIZATION_URL",
        "OCMO_ALLOWED_HOSTS",
        "OCMO_DEBUG",
        "OCMO_API_TITLE",
        "OCMO_API_DESCRIPTION",
        "OCMO_API_VERSION",
        "OCMO_CORS_ALLOWED_ORIGINS",
    }
)

# Variables claimed by the SDK client
_CLIENT_VARS: frozenset[str] = frozenset(
    {
        "OCMO_SERVER",
        "OCMO_NAMESPACE",
        "OCMO_TIMEOUT",
        "OCMO_CONNECT_TIMEOUT",
        "OCMO_RETRIES",
        "OCMO_MAX_CONCURRENCY",
        "OCMO_CA_BUNDLE",
        "OCMO_INSECURE_SKIP_TLS_VERIFY",
        "OCMO_AUTH_MODE",
        "OCMO_OIDC_ISSUER",
        "OCMO_OIDC_TOKEN_URL",
        "OCMO_CLIENT_ID",
        "OCMO_CLIENT_SECRET",
        "OCMO_CLIENT_SECRET_FILE",
        "OCMO_OIDC_SCOPE",
        "OCMO_OIDC_AUDIENCE",
        "OCMO_OIDC_GRANT_TYPE",
        "OCMO_OIDC_USERNAME",
        "OCMO_OIDC_PASSWORD",
        "OCMO_OIDC_PASSWORD_FILE",
        "OCMO_TOKEN",
        "OCMO_TOKEN_FILE",
        "OCMO_CACHE_DIR",
        "OCMO_LOG_LEVEL",
        "OCMO_USER_AGENT_SUFFIX",
        "OCMO_SKIP_VERSION_CHECK",
    }
)

AuthMode = Literal["oidc", "resolver-token", "bearer", "none"]
OidcGrantType = Literal["client_credentials", "password"]


def _env(name: str) -> str | None:
    return os.environ.get(name)


def _env_int(name: str, default: int) -> int:
    val = _env(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError as exc:
        raise OcmoConfigError(f"Environment variable {name} must be an integer, got {val!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    val = _env(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes")


def _read_file_secret(path: str | None, var_name: str) -> str | None:
    """Read a secret from a file path. Returns None if path is None."""
    if path is None:
        return None
    try:
        return Path(path).read_text().strip()
    except OSError as exc:
        raise OcmoConfigError(f"Cannot read secret file for {var_name}: {exc}") from exc


def _resolve_secret(
    direct: str | None,
    file_path: str | None,
    var_name: str,
) -> str | None:
    """Resolve a secret from an explicit value or a file path."""
    if direct is not None and file_path is not None:
        raise OcmoConfigError(f"Specify either {var_name} or {var_name}_FILE, not both.")
    if direct is not None:
        return direct
    return _read_file_secret(file_path, var_name)


def _infer_auth_mode(
    token: str | None,
    client_id: str | None,
) -> AuthMode | None:
    """Infer auth mode from available credentials."""
    has_resolver_token = token is not None and token.startswith("ocmort-")
    has_bearer_token = token is not None and not token.startswith("ocmort-")
    has_client_id = client_id is not None

    candidates = [has_resolver_token, has_bearer_token, has_client_id]
    if sum(candidates) > 1:
        raise OcmoConfigError(
            "Ambiguous authentication configuration: provide only one of "
            "(OCMO_TOKEN starting with 'ocmort-', OCMO_TOKEN with a bearer value, "
            "or OCMO_CLIENT_ID for OIDC)."
        )
    if has_resolver_token:
        return "resolver-token"
    if has_bearer_token:
        return "bearer"
    if has_client_id:
        return "oidc"
    return None


@dataclass
class OcmoConfig:
    """Resolved SDK configuration.

    Build with :func:`OcmoConfig.from_env` (uses environment variables) or
    pass explicit keyword arguments. Explicit arguments always win.
    """

    # Connection
    server: str
    namespace: str | None = None
    timeout: float = 30.0
    connect_timeout: float = 10.0
    retries: int = 3
    max_concurrency: int = 8
    ca_bundle: str | None = None
    insecure_skip_tls_verify: bool = False

    # Authentication
    auth_mode: AuthMode = "none"
    oidc_issuer: str | None = None
    oidc_token_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    oidc_scope: str = "openid"
    oidc_audience: str | None = None
    oidc_grant_type: OidcGrantType = "client_credentials"
    oidc_username: str | None = None
    oidc_password: str | None = None
    oidc_cache_profile: str | None = None
    token: str | None = None

    # Behaviour
    cache_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ocmo"
    )
    log_level: str = "WARNING"
    user_agent_suffix: str | None = None
    skip_version_check: bool = False

    def __post_init__(self) -> None:
        self._validate_server()
        if self.insecure_skip_tls_verify:
            warnings.warn(
                "TLS verification is disabled (OCMO_INSECURE_SKIP_TLS_VERIFY). "
                "This is insecure and must not be used in production.",
                stacklevel=3,
            )

    def _validate_server(self) -> None:
        if not self.server:
            raise OcmoConfigError(
                "OCMO_SERVER is required. Set it to the base URL of the OCMO API, " "e.g. https://ocmo.example.com"
            )
        parsed = urlparse(self.server)
        if parsed.path not in ("", "/"):
            raise OcmoConfigError(
                f"OCMO_SERVER must be a bare origin URL (no path), got {self.server!r}. "
                "The SDK appends /api/v1 automatically."
            )
        if parsed.scheme not in ("http", "https"):
            raise OcmoConfigError(f"OCMO_SERVER must start with http:// or https://, got {self.server!r}.")

    @property
    def base_url(self) -> str:
        """Full API base URL including the versioned prefix."""
        return self.server.rstrip("/") + "/api/v1"

    @classmethod
    def from_env(
        cls,
        *,
        server: str | None = None,
        namespace: str | None = None,
        timeout: float | None = None,
        connect_timeout: float | None = None,
        retries: int | None = None,
        max_concurrency: int | None = None,
        ca_bundle: str | None = None,
        insecure_skip_tls_verify: bool | None = None,
        auth_mode: AuthMode | None = None,
        oidc_issuer: str | None = None,
        oidc_token_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        client_secret_file: str | None = None,
        oidc_scope: str | None = None,
        oidc_audience: str | None = None,
        oidc_grant_type: OidcGrantType | None = None,
        oidc_username: str | None = None,
        oidc_password: str | None = None,
        oidc_password_file: str | None = None,
        oidc_cache_profile: str | None = None,
        token: str | None = None,
        token_file: str | None = None,
        cache_dir: str | Path | None = None,
        log_level: str | None = None,
        user_agent_suffix: str | None = None,
        skip_version_check: bool | None = None,
    ) -> OcmoConfig:
        """Build config from explicit arguments + OCMO_* environment variables."""

        # Resolve file-backed secrets first
        resolved_secret = _resolve_secret(
            client_secret or _env("OCMO_CLIENT_SECRET"),
            client_secret_file or _env("OCMO_CLIENT_SECRET_FILE"),
            "OCMO_CLIENT_SECRET",
        )
        resolved_token = _resolve_secret(
            token or _env("OCMO_TOKEN"),
            token_file or _env("OCMO_TOKEN_FILE"),
            "OCMO_TOKEN",
        )
        resolved_password = _resolve_secret(
            oidc_password or _env("OCMO_OIDC_PASSWORD"),
            oidc_password_file or _env("OCMO_OIDC_PASSWORD_FILE"),
            "OCMO_OIDC_PASSWORD",
        )

        effective_client_id = client_id or _env("OCMO_CLIENT_ID")
        effective_auth_mode_str = auth_mode or _env("OCMO_AUTH_MODE")
        effective_grant_type_str = oidc_grant_type or _env("OCMO_OIDC_GRANT_TYPE") or "client_credentials"
        valid_grant_types = {"client_credentials", "password"}
        if effective_grant_type_str not in valid_grant_types:
            raise OcmoConfigError(
                f"OCMO_OIDC_GRANT_TYPE must be one of {sorted(valid_grant_types)}, "
                f"got {effective_grant_type_str!r}."
            )
        effective_grant_type: OidcGrantType = effective_grant_type_str  # type: ignore[assignment]

        if effective_auth_mode_str is not None:
            valid_modes = {"oidc", "resolver-token", "bearer", "none"}
            if effective_auth_mode_str not in valid_modes:
                raise OcmoConfigError(
                    f"OCMO_AUTH_MODE must be one of {sorted(valid_modes)}, " f"got {effective_auth_mode_str!r}."
                )
            effective_auth_mode: AuthMode = effective_auth_mode_str  # type: ignore[assignment]
        else:
            inferred = _infer_auth_mode(resolved_token, effective_client_id)
            effective_auth_mode = inferred or "none"

        raw_cache_dir = (
            cache_dir
            or _env("OCMO_CACHE_DIR")
            or (Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ocmo")
        )

        return cls(
            server=server or _env("OCMO_SERVER") or "",
            namespace=namespace or _env("OCMO_NAMESPACE"),
            timeout=timeout if timeout is not None else float(_env("OCMO_TIMEOUT") or 30),
            connect_timeout=connect_timeout
            if connect_timeout is not None
            else float(_env("OCMO_CONNECT_TIMEOUT") or 10),
            retries=retries if retries is not None else _env_int("OCMO_RETRIES", 3),
            max_concurrency=max_concurrency if max_concurrency is not None else _env_int("OCMO_MAX_CONCURRENCY", 8),
            ca_bundle=ca_bundle or _env("OCMO_CA_BUNDLE"),
            insecure_skip_tls_verify=(
                insecure_skip_tls_verify
                if insecure_skip_tls_verify is not None
                else _env_bool("OCMO_INSECURE_SKIP_TLS_VERIFY", False)
            ),
            auth_mode=effective_auth_mode,
            oidc_issuer=oidc_issuer or _env("OCMO_OIDC_ISSUER"),
            oidc_token_url=oidc_token_url or _env("OCMO_OIDC_TOKEN_URL"),
            client_id=effective_client_id,
            client_secret=resolved_secret,
            oidc_scope=oidc_scope or _env("OCMO_OIDC_SCOPE") or "openid",
            oidc_audience=oidc_audience or _env("OCMO_OIDC_AUDIENCE"),
            oidc_grant_type=effective_grant_type,
            oidc_username=oidc_username or _env("OCMO_OIDC_USERNAME"),
            oidc_password=resolved_password,
            oidc_cache_profile=oidc_cache_profile,
            token=resolved_token,
            cache_dir=Path(raw_cache_dir),
            log_level=log_level or _env("OCMO_LOG_LEVEL") or "WARNING",
            user_agent_suffix=user_agent_suffix or _env("OCMO_USER_AGENT_SUFFIX"),
            skip_version_check=(
                skip_version_check if skip_version_check is not None else _env_bool("OCMO_SKIP_VERSION_CHECK", False)
            ),
        )
