"""Artifact storage and signed download tokens for resolved configs.

Implements two backends selected by ``OCMO_RESOLVE_ARTIFACT_BACKEND``:

``fs`` (default)
    Writes one content-addressed file per artifact under
    ``OCMO_RESOLVE_ARTIFACT_DIR``.  Filenames are the SHA-256 of the content,
    sharded into two-level subdirectories.  ``/dev/shm`` (tmpfs) is the
    recommended location so artifacts are discarded on host restart.  Files
    older than ``OCMO_RESOLVE_ARTIFACT_MAX_AGE`` are swept by
    ``sweep_fs_artifacts_if_due()`` (throttled, called at resolve time).

``redis``
    Stores artifact bytes at key ``ocmo:resolve:artifact:<sha256>`` with an
    ``EX`` TTL of ``OCMO_RESOLVE_ARTIFACT_MAX_AGE``.  Connection URL comes
    from ``OCMO_RESOLVE_ARTIFACT_REDIS_URL`` (defaults to the shared Redis
    instance).  Optional gzip compression is enabled with
    ``OCMO_RESOLVE_ARTIFACT_REDIS_GZIP=true``.

Both backends support ``X-Accel-Redirect`` offload when
``OCMO_RESOLVE_DOWNLOAD_XACCEL_LOCATION`` is non-empty.

``ArtifactsManager``
    Signed download token minting/verification and the download handler used
    by the API endpoint.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from django.conf import settings

from ..decorators import arg, audit
from ..exceptions import InvalidResolveToken
from ..managers.auth import AuthManager

if settings.OCMO_RESOLVE_ARTIFACT_BACKEND == "redis":
    import redis as redis_lib


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _signing_key() -> bytes:
    # SECRET_KEY is always available in Django; use it as the HMAC key.
    return settings.SECRET_KEY.encode("utf-8")


@dataclass
class ResolveTokenPayload:
    artifact_id: str
    namespace: str
    item_path: str
    identity: str
    exp: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "aid": self.artifact_id,
            "ns": self.namespace,
            "p": self.item_path,
            "sub": self.identity,
            "exp": self.exp,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ResolveTokenPayload:
        return cls(
            artifact_id=raw["aid"],
            namespace=raw["ns"],
            item_path=raw["p"],
            identity=raw["sub"],
            exp=int(raw["exp"]),
        )


def mint_token(
    *,
    artifact_id: str,
    namespace: str,
    item_path: str,
    identity: str,
    ttl_seconds: int | None = None,
) -> str:
    """Create a signed, short-lived token for one resolved artifact."""

    ttl = ttl_seconds if ttl_seconds is not None else settings.OCMO_RESOLVE_URL_TTL
    payload = ResolveTokenPayload(
        artifact_id=artifact_id,
        namespace=namespace,
        item_path=item_path,
        identity=identity,
        exp=int(time.time()) + ttl,
    )
    body = json.dumps(payload.to_dict(), separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_signing_key(), body, hashlib.sha256).digest()
    return f"{_b64url_encode(body)}.{_b64url_encode(sig)}"


def verify_token(token: str) -> ResolveTokenPayload:
    """Validate a signed download token. Raises InvalidResolveToken on failure."""

    try:
        body_b64, sig_b64 = token.split(".", 1)
        body = _b64url_decode(body_b64)
        sig = _b64url_decode(sig_b64)
    except (ValueError, Exception) as exc:  # noqa: BLE001
        raise InvalidResolveToken("Malformed download token") from exc

    expected = hmac.new(_signing_key(), body, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise InvalidResolveToken("Download token signature does not match")

    try:
        payload = ResolveTokenPayload.from_dict(json.loads(body))
    except Exception as exc:  # noqa: BLE001
        raise InvalidResolveToken("Download token payload is unreadable") from exc

    if payload.exp < int(time.time()):
        raise InvalidResolveToken("Download token has expired")

    if not re.fullmatch(r"^[a-f0-9]{64}$", payload.artifact_id):
        raise InvalidResolveToken("Invalid artifact reference in download token")

    return payload


# ---------------------------------------------------------------------------
# Filesystem backend
# ---------------------------------------------------------------------------


class FsArtifactBackend:
    """Content-addressed filesystem storage for resolved artifacts."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.OCMO_RESOLVE_ARTIFACT_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, artifact_id: str) -> Path:
        # Shard into two-level dirs to avoid one giant directory.
        return self.root / artifact_id[:2] / artifact_id[2:4] / artifact_id

    def store(self, content: bytes) -> str:
        """Persist ``content``; return its SHA-256 id (idempotent on duplicates)."""
        artifact_id = hashlib.sha256(content).hexdigest()
        dest = self._path(artifact_id)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".tmp")
            tmp.write_bytes(content)
            os.replace(tmp, dest)
        return artifact_id

    def load(self, artifact_id: str) -> bytes:
        path = self._path(artifact_id)
        if not path.exists():
            raise FileNotFoundError(artifact_id)
        return path.read_bytes()

    def exists(self, artifact_id: str) -> bool:
        return self._path(artifact_id).exists()

    def xaccel_uri(self, artifact_id: str) -> str:
        """Return the internal Nginx URI for X-Accel-Redirect."""
        location = settings.OCMO_RESOLVE_DOWNLOAD_XACCEL_LOCATION.rstrip("/")
        # Sharded path mirrors _path() but relative to the alias root.
        sub = f"{artifact_id[:2]}/{artifact_id[2:4]}/{artifact_id}"
        return f"{location}/{sub}"

    def sweep_expired(self) -> int:
        """Remove files older than ``OCMO_RESOLVE_ARTIFACT_MAX_AGE``. Returns count removed."""
        max_age: int = settings.OCMO_RESOLVE_ARTIFACT_MAX_AGE
        cutoff = time.time() - max_age
        removed = 0
        for p in self.root.rglob("*"):
            if p.is_file() and not p.suffix and p.stat().st_mtime < cutoff:
                try:
                    p.unlink(missing_ok=True)
                    removed += 1
                except OSError:
                    pass
        return removed


# ---------------------------------------------------------------------------
# Redis backend
# ---------------------------------------------------------------------------


class RedisArtifactBackend:
    """Content-addressed Redis storage for resolved artifacts.

    Uses ``settings.OCMO_RESOLVE_ARTIFACT_REDIS_URL``.  Artifacts are stored
    under key ``ocmo:resolve:artifact:<sha256>`` with a TTL of
    ``OCMO_RESOLVE_ARTIFACT_MAX_AGE`` seconds.  Gzip compression is applied
    when ``OCMO_RESOLVE_ARTIFACT_REDIS_GZIP`` is true.

    Uses the ``redis`` client directly instead of Django's cache API because
    ``xaccel_uri()`` must expose the exact Redis key and raw bytes for
    ``X-Accel-Redirect`` (ngx_http_redis).  Django cache mangles keys and
    pickle-serializes values, so it is not compatible with that offload path.
    """

    _KEY_PREFIX = "ocmo:resolve:artifact:"

    def __init__(self):
        self._client = redis_lib.from_url(settings.OCMO_RESOLVE_ARTIFACT_REDIS_URL, decode_responses=False)
        self._gzip: bool = getattr(settings, "OCMO_RESOLVE_ARTIFACT_REDIS_GZIP", False)
        self._ttl: int = settings.OCMO_RESOLVE_ARTIFACT_MAX_AGE

    def _key(self, artifact_id: str) -> str:
        return f"{self._KEY_PREFIX}{artifact_id}"

    def store(self, content: bytes) -> str:
        """Persist ``content`` to Redis; return SHA-256 id."""
        artifact_id = hashlib.sha256(content).hexdigest()
        data = gzip.compress(content) if self._gzip else content
        self._client.set(self._key(artifact_id), data, ex=self._ttl)
        return artifact_id

    def load(self, artifact_id: str) -> bytes:
        data = self._client.get(self._key(artifact_id))
        if data is None:
            raise FileNotFoundError(artifact_id)
        return gzip.decompress(data) if self._gzip else data

    def exists(self, artifact_id: str) -> bool:
        return bool(self._client.exists(self._key(artifact_id)))

    def xaccel_uri(self, artifact_id: str) -> str:
        """Return the internal Nginx URI for X-Accel-Redirect (ngx_http_redis)."""
        location = settings.OCMO_RESOLVE_DOWNLOAD_XACCEL_LOCATION.rstrip("/")
        return f"{location}/{self._key(artifact_id)}"


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------


def get_backend() -> FsArtifactBackend | RedisArtifactBackend:
    backend = getattr(settings, "OCMO_RESOLVE_ARTIFACT_BACKEND", "fs")
    if backend == "redis":
        return RedisArtifactBackend()
    return FsArtifactBackend()


_last_fs_sweep_at: float = 0.0


def sweep_fs_artifacts_if_due() -> int | None:
    """Remove expired fs artifacts when the throttle interval has elapsed.

    Called from the resolve path so ``fs`` deployments enforce
    ``OCMO_RESOLVE_ARTIFACT_MAX_AGE`` without scanning the artifact tree on
    every request.  Returns the number of files removed, or ``None`` when the
    backend is not ``fs`` or the sweep was skipped due to throttling.
    """

    if getattr(settings, "OCMO_RESOLVE_ARTIFACT_BACKEND", "fs") != "fs":
        return None

    interval: int = getattr(settings, "OCMO_RESOLVE_ARTIFACT_SWEEP_INTERVAL", 900)
    now = time.time()
    global _last_fs_sweep_at
    if interval > 0 and (now - _last_fs_sweep_at) < interval:
        return None

    _last_fs_sweep_at = now
    backend = get_backend()
    if not isinstance(backend, FsArtifactBackend):
        return None
    return backend.sweep_expired()


# ---------------------------------------------------------------------------
# ArtifactsManager — download handler
# ---------------------------------------------------------------------------


class ArtifactsManager:
    """Signed artifact download for resolved configs."""

    def __init__(self, namespace, *, auth: AuthManager | None = None) -> None:
        self.namespace = namespace
        self.namespace_name = namespace if isinstance(namespace, str) else namespace.name
        self.auth = auth

    @audit("artifact", object_id_attr=arg("path"), operation="Download artifact")
    def download_artifact(
        self,
        path: str,
        token: str,
    ) -> tuple[Literal["xaccel", "direct"], bytes | str]:
        """Verify the token and return the artifact bytes (or X-Accel URI).

        The signed token is the sole credential; request auth is not consulted.
        """

        payload = verify_token(token)
        if payload.namespace != self.namespace_name:
            raise InvalidResolveToken("Token namespace mismatch")
        if payload.item_path != path:
            raise InvalidResolveToken("Download token path mismatch")
        backend = get_backend()
        xaccel_location = getattr(settings, "OCMO_RESOLVE_DOWNLOAD_XACCEL_LOCATION", "")
        if xaccel_location:
            if not backend.exists(payload.artifact_id):
                raise InvalidResolveToken("Artifact has been evicted; resolve again")
            return "xaccel", backend.xaccel_uri(payload.artifact_id)
        try:
            return "direct", backend.load(payload.artifact_id)
        except FileNotFoundError:
            raise InvalidResolveToken("Artifact has been evicted; resolve again")

    @staticmethod
    def identity_from_auth(auth: AuthManager) -> str:
        """Stable identity string for download-token binding."""

        if auth.is_resolver:
            return f"resolver:{auth.namespace_id}:{auth.resolver_name}"
        user_id = auth.get_claim(AuthManager.user_id_claim())
        return f"user:{user_id}"
