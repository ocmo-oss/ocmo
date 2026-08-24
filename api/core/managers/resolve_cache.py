"""Short-circuit resolve cache backed by Django's cache framework.

Implements the short-circuit cache design from
``docs/features/resolving/README.md#artifact-caching``.

Two-layer design
----------------
Layer 1 — resolution cache (cast-independent)
    Keyed by namespace + path + version + dynamic params.  Stores the
    pre-cast pipeline output (``raw_data``, participants, ``metadata_cast``).
    Skipped when any participant is a secret (avoids secret plaintext at-rest
    in the resolve cache).

Layer 2 — artifact cache (cast-keyed)
    Keyed by namespace + path + version + dynamic params + cast format +
    cast options.  Stores the already-casted artifact references
    (``artifact_id``, ``checksum``) so a fully-identical request is served
    with no pipeline, no cast, and no artifact write.

Cache keys
----------
Layer 1 prefix: ``ocmo:resolve:res:``   (SHA-256 of: ns + path + version + params + no_creds)
Layer 2 prefix: ``ocmo:resolve:art:``   (SHA-256 of: ns + path + version + params + cast + no_creds)

Layer 1 entry
-------------
A JSON-serialisable dict::

    {
        "metadata_cast": {"format": str, "options": {...}} | null,
        "outputs": [
            {
                "name": str,
                "version": int,
                "rendered": bool,
                "format": str,
                "raw_data": <plain dict/list/str>,
                "trace": dict,
            },
            ...
        ],
        "participants": [
            {"kind": str, "path": str, "ref": str, "version": int},
            ...
        ],
    }

Layer 2 entry
-------------
A JSON-serialisable dict::

    {
        "outputs": [
            {
                "name": str,
                "version": int,
                "format": str,
                "artifact_id": str,
                "checksum": str,
                "trace": dict,
            },
            ...
        ],
        "participants": [
            {"kind": str, "path": str, "ref": str, "version": int},
            ...
        ],
    }

Revalidation
------------
Layer 1 — participants only (no artifact check, content not yet stored).
Layer 2 — participants + artifact existence in the backend.

On every cache hit (Layer 1 or Layer 2), after version revalidation:
- **Version check** — each participant still resolves to its stored version.
- **Permission check** — caller holds the same actions as on a full pipeline
  (``config:resolve`` for configs/templates; ``secret:resolve`` for secrets
  unless ``no_creds=true``). Failure returns 403; the entry is not served.

Numeric refs are immutable so their revalidation always passes (we still
verify the object still exists to handle deletions).

``mark-stable=true`` always bypasses both cache layers entirely.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from django.conf import settings
from django.core.cache import caches

from ..exceptions import VersionNotFound
from .artifacts import get_backend
from .tree import TreeManager

logger = logging.getLogger(__name__)

_CACHE_ALIAS = "resolve"


def _hash(parts: dict) -> str:
    raw = json.dumps(parts, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _make_resolution_key(
    namespace_name: str,
    path: str,
    version: str,
    dynamic_params: dict[str, Any] | None,
    *,
    no_creds: bool = False,
) -> str:
    parts = {
        "ns": namespace_name,
        "p": path,
        "v": version,
        "params": sorted((dynamic_params or {}).items()),
        "no_creds": bool(no_creds),
    }
    return "ocmo:resolve:res:" + _hash(parts)


def _make_artifact_key(
    namespace_name: str,
    path: str,
    version: str,
    cast_format: str | None,
    cast_options: dict[str, Any] | None,
    dynamic_params: dict[str, Any] | None,
    *,
    no_creds: bool = False,
) -> str:
    parts = {
        "ns": namespace_name,
        "p": path,
        "v": version,
        "fmt": cast_format or "",
        "opts": sorted((cast_options or {}).items()),
        "params": sorted((dynamic_params or {}).items()),
        "no_creds": bool(no_creds),
    }
    return "ocmo:resolve:art:" + _hash(parts)


def _check_participant(participant: dict[str, Any], namespace) -> bool:
    """Return True if the participant's ref still resolves to the stored version."""
    kind = participant["kind"]
    path = participant["path"]
    ref = participant["ref"]
    stored_version: int = participant["version"]

    if kind not in ("config", "template", "secret"):
        return False

    try:
        item = TreeManager(namespace, path, auth=None).get_item(kind)
        if item is None:
            return False
        current = TreeManager.resolve_version(item, ref).version
    except VersionNotFound:
        return False
    except Exception:  # noqa: BLE001
        return False

    return current == stored_version


class ResolveCacheManager:
    """Short-circuit resolve cache (two-layer)."""

    @staticmethod
    def make_resolution_key(
        namespace_name: str,
        path: str,
        version: str,
        dynamic_params: dict[str, Any] | None,
        *,
        no_creds: bool = False,
    ) -> str:
        """Layer 1 key: cast-independent."""
        return _make_resolution_key(namespace_name, path, version, dynamic_params, no_creds=no_creds)

    @staticmethod
    def make_artifact_key(
        namespace_name: str,
        path: str,
        version: str,
        cast_format: str | None,
        cast_options: dict[str, Any] | None,
        dynamic_params: dict[str, Any] | None,
        *,
        no_creds: bool = False,
    ) -> str:
        """Layer 2 key: includes cast format + options."""
        return _make_artifact_key(
            namespace_name,
            path,
            version,
            cast_format,
            cast_options,
            dynamic_params,
            no_creds=no_creds,
        )

    # ------------------------------------------------------------------
    # Backward-compat alias (make_key was the only public name before)
    # ------------------------------------------------------------------
    # @staticmethod
    # def make_key(
    #     namespace_name: str,
    #     path: str,
    #     version: str,
    #     cast_format: Optional[str],
    #     cast_options: Optional[dict[str, Any]],
    #     dynamic_params: Optional[dict[str, Any]],
    # ) -> str:
    #     """Deprecated alias for make_artifact_key."""
    #     return _make_artifact_key(
    #         namespace_name, path, version, cast_format, cast_options, dynamic_params
    #     )

    @staticmethod
    def get(key: str) -> dict | None:
        try:
            return caches[_CACHE_ALIAS].get(key)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def set(key: str, entry: dict) -> None:
        ttl = getattr(settings, "OCMO_RESOLVE_CACHE_TTL", 3600)
        try:
            caches[_CACHE_ALIAS].set(key, entry, timeout=ttl)
        except Exception:  # noqa: BLE001
            logger.debug("resolve cache: set failed (non-fatal)", exc_info=True)

    @staticmethod
    def participants_valid(entry: dict, namespace) -> bool:
        """Return True when all participants still resolve to their stored versions.

        Used for Layer 1 validation (no artifact check needed).
        """
        for p in entry.get("participants", []):
            if not _check_participant(p, namespace):
                return False
        return True

    @staticmethod
    def is_valid(entry: dict, namespace) -> bool:
        """Return True when all participants are unchanged AND all artifacts still exist.

        Used for Layer 2 (artifact) validation.
        """
        if not ResolveCacheManager.participants_valid(entry, namespace):
            return False
        backend = get_backend()
        for output in entry.get("outputs", []):
            if not backend.exists(output["artifact_id"]):
                return False
        return True
