"""OcmoClient and AsyncOcmoClient — the main entry points for the SDK.

Usage::

    # Sync
    client = OcmoClient()                        # config from OCMO_* env
    client.whoami()
    client.ns("prod").create_lock("app/web", body=...)
    result = client.ns("prod").resolve("app/web")
    print(result["app.json"].text)

    # Async
    async with AsyncOcmoClient() as client:
        result = await client.ns("prod").resolve("app/web")
        print(await result["app.json"].text)

Every REST operation is exposed as a method on :class:`OcmoClient` or
:class:`NamespaceView`. The generated layer under ``ocmo._generated`` is
internal and must not be imported by SDK users.
"""

from __future__ import annotations

import logging
import platform
import re
import time
import warnings
from typing import Any

import httpx

from . import _version
from ._bridge import AsyncTransportBackedClient, TransportBackedClient
from ._facade_impl import (
    _AsyncClientFacadeMixin,
    _AsyncNamespaceFacadeMixin,
    _ClientFacadeMixin,
    _NamespaceFacadeMixin,
)
from ._generated.types import UNSET
from .auth import CredentialProvider, _BearerProvider, _OIDCProvider, _ResolverTokenProvider, build_provider
from .config import OcmoConfig
from .errors import (
    OcmoConfigError,
    OcmoIncompatibleVersionError,
    OcmoTransportError,
    error_body_from_response,
    raise_for_response,
)
from .resolve import (
    AsyncResolveResult,
    ResolveResult,
    build_async_resolve_result,
    build_resolve_result,
)

logger = logging.getLogger("ocmo")

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _encode_resolve_path(path: str) -> str:
    """Encode resolve paths for HTTP routing.

    A lone ``.`` (resolver scope root) is sent as ``@`` because URL stacks
    normalize ``.`` path segments away before the request reaches the API.
    """
    parts: list[str] = []
    for segment in path.split("/"):
        if segment == ".":
            parts.append("@")
        else:
            parts.append(segment)
    return "/".join(parts)


def _parse_semver(version: str) -> tuple[int, int, int]:
    m = _SEMVER_RE.match(version)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _user_agent(suffix: str | None = None) -> str:
    py = platform.python_version()
    plat = platform.system()
    ua = f"ocmo-sdk/{_version.__version__} python/{py} ({plat})"
    if suffix:
        ua += f" {suffix}"
    return ua


def _build_httpx_client(config: OcmoConfig) -> httpx.Client:
    verify: bool | str = True
    if config.insecure_skip_tls_verify:
        verify = False
    elif config.ca_bundle:
        verify = config.ca_bundle

    return httpx.Client(
        base_url=config.base_url,
        timeout=httpx.Timeout(config.timeout, connect=config.connect_timeout),
        verify=verify,
        follow_redirects=False,  # §15.11
        headers={"User-Agent": _user_agent(config.user_agent_suffix)},
    )


def _build_async_httpx_client(config: OcmoConfig) -> httpx.AsyncClient:
    verify: bool | str = True
    if config.insecure_skip_tls_verify:
        verify = False
    elif config.ca_bundle:
        verify = config.ca_bundle

    return httpx.AsyncClient(
        base_url=config.base_url,
        timeout=httpx.Timeout(config.timeout, connect=config.connect_timeout),
        verify=verify,
        follow_redirects=False,
        headers={"User-Agent": _user_agent(config.user_agent_suffix)},
    )


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------


class _VersionChecker:
    """Checks API / SDK version compatibility once per client instance."""

    def __init__(self, sdk_version: str, server_url: str) -> None:
        self._sdk_version = sdk_version
        # The version endpoint lives at /api/version, outside the /api/v1 prefix.
        self._version_url = server_url.rstrip("/") + "/api/version"
        self._checked = False
        self._api_info: dict[str, Any] | None = None

    def check(self, http: httpx.Client) -> dict[str, Any] | None:
        if self._checked:
            return self._api_info
        self._checked = True
        try:
            resp = http.get(self._version_url)
            if resp.status_code != 200:
                return None
            info: dict[str, Any] = resp.json()
            self._api_info = info
            api_version = info.get("version", "0.0.0")
            self._compare(str(api_version))  # may raise OcmoIncompatibleVersionError
            return info
        except OcmoIncompatibleVersionError:
            raise
        except Exception as exc:
            # Network / parse failures are non-blocking — don't prevent the actual call.
            logger.debug("Version check failed (non-blocking): %s", exc)
            return None

    async def check_async(self, http: httpx.AsyncClient) -> dict[str, Any] | None:
        if self._checked:
            return self._api_info
        self._checked = True
        try:
            resp = await http.get(self._version_url)
            if resp.status_code != 200:
                return None
            info: dict[str, Any] = resp.json()
            self._api_info = info
            api_version = info.get("version", "0.0.0")
            self._compare(str(api_version))
            return info
        except OcmoIncompatibleVersionError:
            raise
        except Exception as exc:
            logger.debug("Version check failed (non-blocking): %s", exc)
            return None

    def _compare(self, api_version: str) -> None:
        sdk = _parse_semver(self._sdk_version)
        api = _parse_semver(api_version)

        if sdk[0] != api[0]:
            raise OcmoIncompatibleVersionError(self._sdk_version, api_version)

        # Within same major: warn if outside ±2 minor window
        diff = abs(sdk[1] - api[1])
        if diff > 2:
            warnings.warn(
                f"SDK version {self._sdk_version} is outside the supported compatibility window "
                f"with API version {api_version}. Supported window: ±2 minor versions. "
                "Upgrade one or both components.",
                stacklevel=4,
            )


# ---------------------------------------------------------------------------
# HTTP transport with auth, retries, and error mapping
# ---------------------------------------------------------------------------

_RETRYABLE_METHODS = frozenset({"GET", "HEAD", "PUT", "DELETE"})
_RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})


def _jitter_sleep(attempt: int) -> float:
    """Exponential backoff with full jitter. Returns sleep seconds."""
    import random

    cap = 30.0
    base = min(cap, 0.5 * (2**attempt))
    return random.uniform(0, base)


class _Transport:
    """Sync HTTP transport: auth injection, retries, error normalisation."""

    def __init__(
        self,
        http: httpx.Client,
        provider: CredentialProvider | None,
        retries: int,
        version_checker: _VersionChecker,
    ) -> None:
        self._http = http
        self._provider = provider
        self._retries = retries
        self._version_checker = version_checker
        self._api_info: dict[str, Any] | None = None

    def _inject_auth(self, headers: dict[str, str], path: str = "") -> None:
        if self._provider is None:
            return
        if isinstance(self._provider, _OIDCProvider):
            self._provider.inject_headers(headers, self._api_info)
        elif isinstance(self._provider, _ResolverTokenProvider):
            self._provider.check_path_allowed(path)
            self._provider.inject_headers(headers)
        elif isinstance(self._provider, _BearerProvider):
            self._provider.inject_headers(headers)

    def auth_headers(self, path: str = "") -> dict[str, str]:
        """Return request headers with credentials injected for *path*."""
        headers: dict[str, str] = {}
        self._inject_auth(headers, path)
        return headers

    def _handle_401(self, headers: dict[str, str], path: str) -> bool:
        """Attempt token refresh. Returns True if headers were updated."""
        if isinstance(self._provider, _OIDCProvider):
            new_token = self._provider.refresh(self._api_info)
            headers["Authorization"] = f"Bearer {new_token}"
            return True
        if isinstance(self._provider, _BearerProvider):
            return self._provider.refresh_from_file()
        return False

    def request_raw(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Like :meth:`request`, but returns the response without raising on HTTP errors."""
        headers: dict[str, str] = dict(kwargs.pop("headers", {}))
        self._inject_auth(headers, url)

        is_retryable = method.upper() in _RETRYABLE_METHODS
        attempt = 0
        last_exc: Exception | None = None

        while attempt <= self._retries:
            try:
                t0 = time.monotonic()
                resp = self._http.request(method, url, headers=headers, **kwargs)
                elapsed = time.monotonic() - t0
                logger.debug(
                    "%s %s → %s in %.3fs cache=%s",
                    method,
                    url,
                    resp.status_code,
                    elapsed,
                    resp.headers.get("X-Ocmo-Resolve-Cache", "-"),
                )
            except httpx.TransportError as exc:
                last_exc = exc
                if is_retryable and attempt < self._retries:
                    time.sleep(_jitter_sleep(attempt))
                    attempt += 1
                    continue
                raise OcmoTransportError(str(exc)) from exc

            if resp.status_code == 401 and attempt == 0:
                refreshed = self._handle_401(headers, url)
                if refreshed:
                    attempt += 1
                    continue

            if resp.status_code in _RETRYABLE_STATUSES and is_retryable and attempt < self._retries:
                retry_after = float(resp.headers.get("Retry-After", 0))
                time.sleep(retry_after or _jitter_sleep(attempt))
                attempt += 1
                continue

            return resp

        raise OcmoTransportError(f"Request failed after {self._retries} retries: {last_exc}")

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        resp = self.request_raw(method, url, **kwargs)
        if not resp.is_success:
            body = error_body_from_response(
                status_code=resp.status_code,
                content=resp.content,
                content_type=resp.headers.get("content-type", ""),
            )
            raise_for_response(
                status_code=resp.status_code,
                method=method,
                path=url,
                body=body,
            )
        return resp

    def ensure_api_info(self) -> dict[str, Any] | None:
        if self._api_info is None:
            self._api_info = self._version_checker.check(self._http)
        return self._api_info


class _AsyncTransport:
    """Async HTTP transport."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        provider: CredentialProvider | None,
        retries: int,
        version_checker: _VersionChecker,
    ) -> None:
        self._http = http
        self._provider = provider
        self._retries = retries
        self._version_checker = version_checker
        self._api_info: dict[str, Any] | None = None

    def _inject_auth(self, headers: dict[str, str], path: str = "") -> None:
        if self._provider is None:
            return
        if isinstance(self._provider, _OIDCProvider):
            self._provider.inject_headers(headers, self._api_info)
        elif isinstance(self._provider, _ResolverTokenProvider):
            self._provider.check_path_allowed(path)
            self._provider.inject_headers(headers)
        elif isinstance(self._provider, _BearerProvider):
            self._provider.inject_headers(headers)

    def auth_headers(self, path: str = "") -> dict[str, str]:
        """Return request headers with credentials injected for *path*."""
        headers: dict[str, str] = {}
        self._inject_auth(headers, path)
        return headers

    def _handle_401(self, headers: dict[str, str], path: str) -> bool:
        if isinstance(self._provider, _OIDCProvider):
            new_token = self._provider.refresh(self._api_info)
            headers["Authorization"] = f"Bearer {new_token}"
            return True
        if isinstance(self._provider, _BearerProvider):
            return self._provider.refresh_from_file()
        return False

    async def request_raw(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        import asyncio as _asyncio

        headers: dict[str, str] = dict(kwargs.pop("headers", {}))
        self._inject_auth(headers, url)

        is_retryable = method.upper() in _RETRYABLE_METHODS
        attempt = 0

        while attempt <= self._retries:
            try:
                t0 = time.monotonic()
                resp = await self._http.request(method, url, headers=headers, **kwargs)
                elapsed = time.monotonic() - t0
                logger.debug(
                    "%s %s → %s in %.3fs cache=%s",
                    method,
                    url,
                    resp.status_code,
                    elapsed,
                    resp.headers.get("X-Ocmo-Resolve-Cache", "-"),
                )
            except httpx.TransportError as exc:
                if is_retryable and attempt < self._retries:
                    await _asyncio.sleep(_jitter_sleep(attempt))
                    attempt += 1
                    continue
                raise OcmoTransportError(str(exc)) from exc

            if resp.status_code == 401 and attempt == 0:
                refreshed = self._handle_401(headers, url)
                if refreshed:
                    attempt += 1
                    continue

            if resp.status_code in _RETRYABLE_STATUSES and is_retryable and attempt < self._retries:
                retry_after = float(resp.headers.get("Retry-After", 0))
                await _asyncio.sleep(retry_after or _jitter_sleep(attempt))
                attempt += 1
                continue

            return resp

        raise OcmoTransportError(f"Async request failed after {self._retries} retries.")

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        resp = await self.request_raw(method, url, **kwargs)
        if not resp.is_success:
            body = error_body_from_response(
                status_code=resp.status_code,
                content=resp.content,
                content_type=resp.headers.get("content-type", ""),
            )
            raise_for_response(
                status_code=resp.status_code,
                method=method,
                path=url,
                body=body,
            )
        return resp

    async def ensure_api_info(self) -> dict[str, Any] | None:
        if self._api_info is None:
            self._api_info = await self._version_checker.check_async(self._http)
        return self._api_info


# ---------------------------------------------------------------------------
# Dynamic query parameter helpers (§6.5)
# ---------------------------------------------------------------------------


def _build_params(
    *,
    params: dict[str, str] | None = None,
    cast_options: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Serialise dynamic query params to the API's naming conventions."""
    result: dict[str, str] = {}
    if extra:
        result.update({k: str(v) for k, v in extra.items() if v is not None})
    if params:
        for k, v in params.items():
            result[f"param_{k}"] = str(v)
    if cast_options:
        for k, v in cast_options.items():
            result[f"cast_option_{k}"] = str(v)
    return result


# ---------------------------------------------------------------------------
# Namespace-scoped views
# ---------------------------------------------------------------------------


class NamespaceView(_NamespaceFacadeMixin):
    """Namespace-bound view that pre-fills the ``namespace`` argument."""

    def __init__(self, client: OcmoClient, namespace: str) -> None:
        self._client = client
        self._namespace = namespace

    @property
    def _api(self) -> TransportBackedClient:
        return self._client._api

    def resolve(
        self,
        path: str,
        *,
        version: str = "latest",
        cast: str | None = None,
        trace_only: bool = False,
        mark_stable: bool = False,
        ignore_configs_with_missing_tags: bool = False,
        no_creds: bool = False,
        params: dict[str, str] | None = None,
        cast_options: dict[str, str] | None = None,
    ) -> ResolveResult:
        """Resolve a config or folder path.

        The ``python`` cast is SDK-local: it sends ``json`` on the wire and
        parses the result into native Python objects. The wire format is
        recorded in ``result.wire_cast`` and the audit log will show ``json``.
        """
        return self._client._resolve(
            namespace=self._namespace,
            path=path,
            version=version,
            cast=cast,
            trace_only=trace_only,
            mark_stable=mark_stable,
            ignore_configs_with_missing_tags=ignore_configs_with_missing_tags,
            no_creds=no_creds,
            params=params,
            cast_options=cast_options,
        )


class AsyncNamespaceView(_AsyncNamespaceFacadeMixin):
    """Async namespace-bound view."""

    def __init__(self, client: AsyncOcmoClient, namespace: str) -> None:
        self._client = client
        self._namespace = namespace

    @property
    def _api(self) -> AsyncTransportBackedClient:
        return self._client._api

    async def resolve(
        self,
        path: str,
        *,
        version: str = "latest",
        cast: str | None = None,
        trace_only: bool = False,
        mark_stable: bool = False,
        ignore_configs_with_missing_tags: bool = False,
        no_creds: bool = False,
        params: dict[str, str] | None = None,
        cast_options: dict[str, str] | None = None,
    ) -> AsyncResolveResult:
        return await self._client._resolve(
            namespace=self._namespace,
            path=path,
            version=version,
            cast=cast,
            trace_only=trace_only,
            mark_stable=mark_stable,
            ignore_configs_with_missing_tags=ignore_configs_with_missing_tags,
            no_creds=no_creds,
            params=params,
            cast_options=cast_options,
        )


# ---------------------------------------------------------------------------
# Main clients
# ---------------------------------------------------------------------------


class OcmoClient(_ClientFacadeMixin):
    """Synchronous OCMO API client.

    Args:
        config: Explicit :class:`~ocmo.config.OcmoConfig`. When omitted,
            configuration is resolved from OCMO_* environment variables.
        **kwargs: Forwarded to :meth:`OcmoConfig.from_env` when *config* is
            omitted (convenience for quick scripts).

    Every generated REST operation is available as a method on this client or
    on :meth:`ns` (for namespace-scoped calls). Do not import ``ocmo._generated``.
    """

    def __init__(self, config: OcmoConfig | None = None, **kwargs: Any) -> None:
        if config is None:
            config = OcmoConfig.from_env(**kwargs)
        self._config = config
        self._http = _build_httpx_client(config)
        self._provider = build_provider(config)
        self._version_checker = _VersionChecker(_version.__version__, config.server)
        self._transport = _Transport(self._http, self._provider, config.retries, self._version_checker)
        self._api = TransportBackedClient(self._transport)

        logging.getLogger("ocmo").setLevel(config.log_level.upper())

    def ns(self, namespace: str | None = None) -> NamespaceView:
        """Return a namespace-bound view.

        If *namespace* is omitted, the default from config (``OCMO_NAMESPACE``)
        is used. Raises :exc:`~ocmo.errors.OcmoConfigError` if neither is set.
        """
        ns = namespace or self._config.namespace
        if not ns:
            raise OcmoConfigError("No namespace specified. Pass namespace= or set OCMO_NAMESPACE.")
        return NamespaceView(self, ns)

    def _resolve(
        self,
        *,
        namespace: str,
        path: str,
        version: str,
        cast: str | None,
        trace_only: bool,
        mark_stable: bool,
        ignore_configs_with_missing_tags: bool,
        no_creds: bool,
        params: dict[str, str] | None,
        cast_options: dict[str, str] | None,
    ) -> ResolveResult:
        # §9.4: translate python cast to json on the wire
        wire_cast = "json" if cast == "python" else cast

        query = _build_params(
            params=params,
            cast_options=cast_options,
            extra={
                "version": version,
                "cast": wire_cast,
                "trace_only": str(trace_only).lower() if trace_only else None,
                "mark-stable": str(mark_stable).lower() if mark_stable else None,
                "ignore-configs-with-missing-tags": (
                    str(ignore_configs_with_missing_tags).lower() if ignore_configs_with_missing_tags else None
                ),
                "no-creds": str(no_creds).lower() if no_creds else None,
            },
        )

        url = f"/ns/{namespace}/~resolve/{_encode_resolve_path(path)}"
        resp = self._transport.request("GET", url, params=query)
        cache_status = resp.headers.get("X-Ocmo-Resolve-Cache")
        data = resp.json()

        return build_resolve_result(
            data,
            http=self._http,
            transport=self._transport,
            server_origin=self._config.server,
            cast=cast,
            cache_status=cache_status,
        )

    def version_info(self) -> dict[str, Any] | None:
        """Return cached API version info (fetches once on first call)."""
        return self._transport.ensure_api_info()

    def version(self, *, notice: Any = UNSET) -> Any:
        """Return API version info, or local product metadata when ``notice=True``."""
        if notice is True:
            from .notice import product_version_info

            return product_version_info(include_notice=True)
        return super().version(notice=notice)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> OcmoClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncOcmoClient(_AsyncClientFacadeMixin):
    """Asynchronous OCMO API client.

    Usage::

        async with AsyncOcmoClient() as client:
            result = await client.ns("prod").resolve("app/web")
    """

    def __init__(self, config: OcmoConfig | None = None, **kwargs: Any) -> None:
        if config is None:
            config = OcmoConfig.from_env(**kwargs)
        self._config = config
        self._http = _build_async_httpx_client(config)
        self._provider = build_provider(config)
        self._version_checker = _VersionChecker(_version.__version__, config.server)
        self._transport = _AsyncTransport(self._http, self._provider, config.retries, self._version_checker)
        self._api = AsyncTransportBackedClient(self._transport)

        logging.getLogger("ocmo").setLevel(config.log_level.upper())

    def ns(self, namespace: str | None = None) -> AsyncNamespaceView:
        ns = namespace or self._config.namespace
        if not ns:
            raise OcmoConfigError("No namespace specified. Pass namespace= or set OCMO_NAMESPACE.")
        return AsyncNamespaceView(self, ns)

    async def _resolve(
        self,
        *,
        namespace: str,
        path: str,
        version: str,
        cast: str | None,
        trace_only: bool,
        mark_stable: bool,
        ignore_configs_with_missing_tags: bool,
        no_creds: bool,
        params: dict[str, str] | None,
        cast_options: dict[str, str] | None,
    ) -> AsyncResolveResult:
        wire_cast = "json" if cast == "python" else cast

        query = _build_params(
            params=params,
            cast_options=cast_options,
            extra={
                "version": version,
                "cast": wire_cast,
                "trace_only": str(trace_only).lower() if trace_only else None,
                "mark-stable": str(mark_stable).lower() if mark_stable else None,
                "ignore-configs-with-missing-tags": (
                    str(ignore_configs_with_missing_tags).lower() if ignore_configs_with_missing_tags else None
                ),
                "no-creds": str(no_creds).lower() if no_creds else None,
            },
        )

        url = f"/ns/{namespace}/~resolve/{_encode_resolve_path(path)}"
        resp = await self._transport.request("GET", url, params=query)
        cache_status = resp.headers.get("X-Ocmo-Resolve-Cache")
        data = resp.json()

        return build_async_resolve_result(
            data,
            http=self._http,
            transport=self._transport,
            server_origin=self._config.server,
            cast=cast,
            cache_status=cache_status,
        )

    async def version_info(self) -> dict[str, Any] | None:
        return await self._transport.ensure_api_info()

    async def version(self, *, notice: Any = UNSET) -> Any:
        """Return API version info, or local product metadata when ``notice=True``."""
        if notice is True:
            from .notice import product_version_info

            return product_version_info(include_notice=True)
        return await super().version(notice=notice)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncOcmoClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
