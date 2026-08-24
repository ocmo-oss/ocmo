"""Lazy artifact model for resolved configs.

``ResolveResult`` is built from the resolve HTTP response without fetching any
artifact. Downloads happen on first access to ``item.bytes``, ``item.text``, or
``item.data`` (lazy, memoised, thread-safe).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx

from .errors import ArtifactExpiredError, ChecksumMismatchError, NoArtifactError
from .structured import _SENTINEL, StructuredMixin

logger = logging.getLogger("ocmo")

_STRUCTURED_FORMATS = frozenset({"json", "yaml"})
_DOWNLOAD_PATH_MARKER = "/~download/"


def _normalize_artifact_url(url: str, server_origin: str) -> str:
    """Validate and normalize a signed artifact URL against OCMO_SERVER.

    Exact origin match is accepted. When the URL is an OCMO download path and the
    hostname matches but the port differs (common behind reverse proxies), rewrite
    the origin to ``server_origin``.
    """
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    server = urlparse(server_origin)

    if parsed.scheme == server.scheme and parsed.netloc == server.netloc:
        return url

    if _DOWNLOAD_PATH_MARKER in parsed.path and parsed.hostname and server.hostname:
        if parsed.hostname.lower() == server.hostname.lower():
            return urlunparse(parsed._replace(scheme=server.scheme, netloc=server.netloc))

    raise ValueError(f"Artifact URL {url!r} does not share the server origin " f"{server_origin!r}. Refusing to fetch.")


def _artifact_request_path(url: str, server_origin: str) -> str:
    """Map a signed artifact URL to the transport-relative API path."""
    from urllib.parse import urlparse

    normalized = _normalize_artifact_url(url, server_origin)
    path = urlparse(normalized).path
    api_prefix = "/api/v1"
    if path.startswith(api_prefix):
        path = path[len(api_prefix) :]
    return path or "/"


# ---------------------------------------------------------------------------
# Resolver configuration (read-only, §12)
# ---------------------------------------------------------------------------


class ResolverHooks:
    """Hook command strings as configured on the effective resolver.

    WARNING: These are server-supplied strings. The SDK MUST NOT execute them.
    Executing server-supplied commands is a remote-code-execution primitive.
    That decision belongs to the CLI where a human has consented.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def validate(self) -> str | None:
        return self._data.get("validate")

    @property
    def validate_all(self) -> str | None:
        return self._data.get("validate_all")

    @property
    def post_resolve(self) -> str | None:
        return self._data.get("post_resolve")

    @property
    def post_resolve_all(self) -> str | None:
        return self._data.get("post_resolve_all")

    def __repr__(self) -> str:
        return f"ResolverHooks({self._data!r})"


class ResolverConfig:
    """Effective resolver configuration surfaced in the resolve response."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def cast(self) -> str | None:
        return self._data.get("cast")

    @property
    def parameters(self) -> dict[str, Any]:
        return dict(self._data.get("parameters") or {})

    @property
    def hooks(self) -> ResolverHooks:
        return ResolverHooks(self._data.get("hooks") or {})

    def __repr__(self) -> str:
        return f"ResolverConfig(cast={self.cast!r})"


# ---------------------------------------------------------------------------
# Resolved item
# ---------------------------------------------------------------------------


class ResolvedItem(StructuredMixin):
    """One resolved output document.

    Artifact bytes are fetched lazily on first access and memoised.
    Thread-safe: only one HTTP request is issued even under concurrent access.
    """

    def __init__(
        self,
        *,
        name: str,
        version: int,
        format: str,
        url: str | None,
        checksum: str | None,
        trace: dict[str, Any],
        trace_only: bool,
        http: httpx.Client,
        server_origin: str,
        transport: Any | None = None,
    ) -> None:
        self.name = name
        self.version = version
        self.format = format
        self.url = url
        self.checksum = checksum
        self.trace = trace

        self._trace_only = trace_only
        self._http = http
        self._transport = transport
        self._server_origin = server_origin
        self._lock = threading.Lock()
        self._bytes: bytes | None = None
        self._parsed_data: Any = _SENTINEL

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_url(self) -> str:
        if self._trace_only:
            raise NoArtifactError(self.name)
        if not self.url:
            raise NoArtifactError(self.name)
        return _normalize_artifact_url(self.url, self._server_origin)

    def _get_bytes(self) -> bytes:
        with self._lock:
            if self._bytes is not None:
                return self._bytes
            url = self._validate_url()
            path = _artifact_request_path(url, self._server_origin)
            logger.debug("Fetching artifact %r from %s", self.name, path)
            try:
                if self._transport is not None:
                    resp = self._transport.request_raw("GET", path)
                else:
                    resp = self._http.get(url)
            except httpx.HTTPError as exc:
                raise ArtifactExpiredError(
                    f"Failed to download artifact {self.name!r}: {exc}. " "The download URL may have expired."
                ) from exc
            if resp.status_code == 401:
                raise ArtifactExpiredError(
                    f"Download URL for {self.name!r} returned 401. "
                    "The signed URL has expired. Re-resolve to obtain a fresh URL."
                )
            resp.raise_for_status()
            data = resp.content
            if self.checksum:
                self._verify_checksum(data)
            self._bytes = data
            return self._bytes

    def _verify_checksum(self, data: bytes) -> None:
        if not self.checksum:
            return
        # Expected format: "<algo>:<hex>", e.g. "sha256:abc123"
        if ":" in self.checksum:
            algo, expected = self.checksum.split(":", 1)
        else:
            algo, expected = "sha256", self.checksum
        actual = hashlib.new(algo, data).hexdigest()
        if actual != expected:
            raise ChecksumMismatchError(self.name, self.checksum, f"{algo}:{actual}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def bytes(self) -> bytes:
        """Raw artifact bytes. Fetched once, memoised."""
        return self._get_bytes()

    @property
    def text(self) -> str:
        """Artifact decoded as UTF-8 text."""
        return self._get_bytes().decode("utf-8")

    @contextmanager
    def open(self) -> Generator[httpx.Response, None, None]:
        """Stream artifact bytes without buffering the whole body.

        Yields the streaming :class:`httpx.Response`. Use as a context manager::

            with item.open() as resp:
                for chunk in resp.iter_bytes():
                    dest.write(chunk)
        """
        url = self._validate_url()
        path = _artifact_request_path(url, self._server_origin)
        if self._transport is not None:
            headers = self._transport.auth_headers(path)
            stream_ctx = self._http.stream("GET", path, headers=headers)
        else:
            stream_ctx = self._http.stream("GET", url)
        with stream_ctx as resp:
            resp.raise_for_status()
            yield resp

    def save(self, path: str | Path, *, create_parents: bool = False) -> None:
        """Save artifact to *path* atomically (temp file + os.replace).

        Args:
            path: Destination file path.
            create_parents: If True, create parent directories.
        """
        dest = Path(path)
        if create_parents:
            dest.parent.mkdir(parents=True, exist_ok=True)
        data = self._get_bytes()
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        try:
            tmp.write_bytes(data)
            os.replace(tmp, dest)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def __repr__(self) -> str:
        return f"ResolvedItem(name={self.name!r}, format={self.format!r}, version={self.version})"


# ---------------------------------------------------------------------------
# Async variant
# ---------------------------------------------------------------------------


class AsyncResolvedItem(StructuredMixin):
    """Async counterpart of :class:`ResolvedItem`."""

    def __init__(
        self,
        *,
        name: str,
        version: int,
        format: str,
        url: str | None,
        checksum: str | None,
        trace: dict[str, Any],
        trace_only: bool,
        http: httpx.AsyncClient,
        server_origin: str,
        transport: Any | None = None,
    ) -> None:
        self.name = name
        self.version = version
        self.format = format
        self.url = url
        self.checksum = checksum
        self.trace = trace

        self._trace_only = trace_only
        self._http = http
        self._transport = transport
        self._server_origin = server_origin
        self._lock = asyncio.Lock()
        self._bytes: bytes | None = None
        self._parsed_data: Any = _SENTINEL

    def _validate_url(self) -> str:
        if self._trace_only:
            raise NoArtifactError(self.name)
        if not self.url:
            raise NoArtifactError(self.name)
        return _normalize_artifact_url(self.url, self._server_origin)

    def _verify_checksum(self, data: bytes) -> None:
        if not self.checksum:
            return
        if ":" in self.checksum:
            algo, expected = self.checksum.split(":", 1)
        else:
            algo, expected = "sha256", self.checksum
        actual = hashlib.new(algo, data).hexdigest()
        if actual != expected:
            raise ChecksumMismatchError(self.name, self.checksum, f"{algo}:{actual}")

    def _get_bytes(self) -> bytes:
        raise RuntimeError("Use 'await item.bytes_async()' for async items.")

    async def get_bytes(self) -> bytes:
        async with self._lock:
            if self._bytes is not None:
                return self._bytes
            url = self._validate_url()
            path = _artifact_request_path(url, self._server_origin)
            try:
                if self._transport is not None:
                    resp = await self._transport.request_raw("GET", path)
                else:
                    resp = await self._http.get(url)
            except httpx.HTTPError as exc:
                raise ArtifactExpiredError(f"Failed to download artifact {self.name!r}: {exc}.") from exc
            if resp.status_code == 401:
                raise ArtifactExpiredError(
                    f"Download URL for {self.name!r} returned 401. Re-resolve to get a fresh URL."
                )
            resp.raise_for_status()
            data = resp.content
            if self.checksum:
                self._verify_checksum(data)
            self._bytes = data
            return self._bytes

    async def bytes_async(self) -> bytes:
        """Fetch raw artifact bytes asynchronously. Memoised."""
        return await self.get_bytes()

    async def text_async(self) -> str:
        """Fetch artifact bytes and decode as UTF-8 asynchronously."""
        return (await self.get_bytes()).decode("utf-8")

    def __repr__(self) -> str:
        return f"AsyncResolvedItem(name={self.name!r}, format={self.format!r})"


# ---------------------------------------------------------------------------
# Resolve result
# ---------------------------------------------------------------------------


class ResolveResult:
    """Result of a resolve call.

    Iterating yields :class:`ResolvedItem` objects without triggering any
    artifact downloads. Downloads happen only when ``item.bytes`` (etc.) is
    accessed.

    The ``python`` cast is an SDK-local pseudo-format. When requested,
    ``wire_cast`` records the actual format sent on the wire (``json``),
    and ``cast`` reports ``python`` as requested.
    """

    def __init__(
        self,
        *,
        items: list[ResolvedItem],
        cache_status: str | None,
        trace_only: bool,
        root: dict[str, Any] | None,
        resolver: ResolverConfig | None,
        cast: str | None,
        wire_cast: str | None,
    ) -> None:
        self._items = items
        self._by_name: dict[str, ResolvedItem] = {item.name: item for item in items}
        self.cache_status = cache_status
        self.trace_only = trace_only
        self.root = root
        self.resolver = resolver
        self.cast = cast
        self.wire_cast = wire_cast

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[ResolvedItem]:
        return iter(self._items)

    def __getitem__(self, name: str) -> ResolvedItem:
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"No resolved item named {name!r}. Available: {list(self._by_name)}")

    @property
    def items(self) -> list[ResolvedItem]:
        return list(self._items)

    def prefetch(self, max_workers: int | None = None) -> None:
        """Download all artifacts eagerly in parallel threads."""
        from concurrent.futures import ThreadPoolExecutor

        workers = max_workers or int(os.environ.get("OCMO_MAX_CONCURRENCY", 8))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(item._get_bytes) for item in self._items if not item._trace_only]
            for f in futures:
                f.result()

    def save_all(
        self,
        directory: str | Path,
        *,
        overwrite: bool = False,
    ) -> None:
        """Write every item to ``directory / item.name``.

        Path safety (§11):
        - Rejects absolute names.
        - Rejects names with ``..`` segments.
        - Rejects names that resolve outside *directory* after normalisation.
        - Does not follow symlinks when creating parents or writing.
        - Refuses to overwrite existing files unless ``overwrite=True``.
        """
        base = Path(directory).resolve()
        collisions: list[str] = []
        for item in self._items:
            dest = _safe_join(base, item.name)
            if not overwrite and dest.exists():
                collisions.append(item.name)
        if collisions:
            raise FileExistsError(
                f"save_all() would overwrite existing files: {collisions}. " "Pass overwrite=True to allow it."
            )
        for item in self._items:
            dest = _safe_join(base, item.name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = item._get_bytes()
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            try:
                tmp.write_bytes(data)
                os.replace(tmp, dest)
            except Exception:
                tmp.unlink(missing_ok=True)
                raise

    def __repr__(self) -> str:
        return f"ResolveResult(items={len(self._items)}, cache_status={self.cache_status!r}, " f"cast={self.cast!r})"


class AsyncResolveResult:
    """Async counterpart of :class:`ResolveResult`."""

    def __init__(
        self,
        *,
        items: list[AsyncResolvedItem],
        cache_status: str | None,
        trace_only: bool,
        root: dict[str, Any] | None,
        resolver: ResolverConfig | None,
        cast: str | None,
        wire_cast: str | None,
    ) -> None:
        self._items = items
        self._by_name: dict[str, AsyncResolvedItem] = {item.name: item for item in items}
        self.cache_status = cache_status
        self.trace_only = trace_only
        self.root = root
        self.resolver = resolver
        self.cast = cast
        self.wire_cast = wire_cast

    def __len__(self) -> int:
        return len(self._items)

    def __aiter__(self) -> Iterator[AsyncResolvedItem]:
        return iter(self._items)

    def __getitem__(self, name: str) -> AsyncResolvedItem:
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"No resolved item named {name!r}.")

    @property
    def items(self) -> list[AsyncResolvedItem]:
        return list(self._items)

    async def prefetch(self, max_concurrency: int | None = None) -> None:
        """Download all artifacts eagerly with bounded concurrency."""
        sem = asyncio.Semaphore(max_concurrency or int(os.environ.get("OCMO_MAX_CONCURRENCY", 8)))

        async def _fetch(item: AsyncResolvedItem) -> None:
            async with sem:
                await item.get_bytes()

        await asyncio.gather(*[_fetch(i) for i in self._items if not i._trace_only])

    def __repr__(self) -> str:
        return f"AsyncResolveResult(items={len(self._items)}, " f"cache_status={self.cache_status!r})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_join(base: Path, name: str) -> Path:
    """Join *base* and *name*, raising on zip-slip and absolute names."""
    if os.path.isabs(name):
        raise ValueError(f"Refusing to write to absolute path: {name!r}")
    dest = (base / name).resolve()
    try:
        dest.relative_to(base)
    except ValueError:
        raise ValueError(f"Refusing to write {name!r}: path escapes the target directory.")
    # Reject '..' segments before resolution so we catch them explicitly
    parts = Path(name).parts
    if ".." in parts:
        raise ValueError(f"Refusing to write {name!r}: contains '..' segment.")
    # Refuse to follow symlinks in parent creation
    parent = dest.parent
    if parent.is_symlink():
        raise ValueError(f"Refusing to create directory {parent}: it is a symlink.")
    return dest


def build_resolve_result(
    response_data: dict[str, Any],
    *,
    http: httpx.Client,
    server_origin: str,
    cast: str | None,
    cache_status: str | None,
    transport: Any | None = None,
) -> ResolveResult:
    """Construct a :class:`ResolveResult` from the raw API response dict."""
    trace_only = bool(response_data.get("trace_only"))
    raw_items = response_data.get("items") or []
    root = response_data.get("root")
    raw_resolver = response_data.get("resolver")
    resolver = ResolverConfig(raw_resolver) if raw_resolver else None

    # §9.4: python cast — translate to json on wire, report python in result
    wire_cast = cast
    if cast == "python":
        wire_cast = "json"

    items = [
        ResolvedItem(
            name=item["name"],
            version=item.get("version", 0),
            format=item.get("format", "raw"),
            url=item.get("url"),
            checksum=item.get("checksum"),
            trace=item.get("trace") or {},
            trace_only=trace_only,
            http=http,
            server_origin=server_origin,
            transport=transport,
        )
        for item in raw_items
    ]

    result = ResolveResult(
        items=items,
        cache_status=cache_status,
        trace_only=trace_only,
        root=root,
        resolver=resolver,
        cast=cast,
        wire_cast=wire_cast,
    )

    # §9.4: post-process python cast items
    if cast == "python":
        _apply_python_cast(result)

    return result


def _apply_python_cast(result: ResolveResult) -> None:
    """Parse json bytes into Python objects for all items in a python-cast result."""
    import json as _json

    for item in result._items:
        if item._bytes is not None:
            try:
                item._parsed_data = _json.loads(item._bytes)
            except Exception:
                pass


def build_async_resolve_result(
    response_data: dict[str, Any],
    *,
    http: httpx.AsyncClient,
    server_origin: str,
    cast: str | None,
    cache_status: str | None,
    transport: Any | None = None,
) -> AsyncResolveResult:
    """Construct an :class:`AsyncResolveResult` from the raw API response dict."""
    trace_only = bool(response_data.get("trace_only"))
    raw_items = response_data.get("items") or []
    root = response_data.get("root")
    raw_resolver = response_data.get("resolver")
    resolver = ResolverConfig(raw_resolver) if raw_resolver else None

    wire_cast = cast
    if cast == "python":
        wire_cast = "json"

    items = [
        AsyncResolvedItem(
            name=item["name"],
            version=item.get("version", 0),
            format=item.get("format", "raw"),
            url=item.get("url"),
            checksum=item.get("checksum"),
            trace=item.get("trace") or {},
            trace_only=trace_only,
            http=http,
            server_origin=server_origin,
            transport=transport,
        )
        for item in raw_items
    ]

    return AsyncResolveResult(
        items=items,
        cache_status=cache_status,
        trace_only=trace_only,
        root=root,
        resolver=resolver,
        cast=cast,
        wire_cast=wire_cast,
    )
