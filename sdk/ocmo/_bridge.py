"""Internal bridge between hand-written transport and generated API clients."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, TypeVar
from urllib.parse import unquote

import httpx

from ocmo._generated.models.error_schema import ErrorSchema
from ocmo._generated.types import Response
from ocmo.errors import error_body_from_response, raise_for_response

if TYPE_CHECKING:
    from .client import _AsyncTransport, _Transport

T = TypeVar("T")


_API_V1_PREFIX = "/api/v1"
_EMPTY_JSON_BODY = b'{"details":""}'
_NS_DELETE_RE = re.compile(r"/ns/([^/?#]+)/?$")


def _synthetic_204_body(response: httpx.Response) -> bytes:
    """Build JSON for empty 204 responses that generated parsers still decode."""
    request = response.request
    if request is not None and request.method.upper() == "DELETE":
        match = _NS_DELETE_RE.search(str(request.url))
        if match is not None:
            namespace = unquote(match.group(1))
            return json.dumps({"namespace": namespace, "success": True}).encode()
    return _EMPTY_JSON_BODY


def _normalize_no_content_response(response: httpx.Response) -> httpx.Response:
    """RFC 7231 forbids a message body on 204/205; some generated parsers still call ``response.json()``."""
    if int(response.status_code) not in {204, 205}:
        return response
    if response.content.strip():
        return response
    return httpx.Response(
        status_code=response.status_code,
        headers=response.headers,
        content=_synthetic_204_body(response),
        request=response.request,
    )


def _api_root_origin(base_url: str) -> str | None:
    base = base_url.rstrip("/")
    if base.endswith("/api/v1"):
        return base[: -len("/api/v1")]
    return None


def _resolve_generated_url(http_client: httpx.Client | httpx.AsyncClient, url: str) -> tuple[str, bool]:
    """Map generated OpenAPI paths to transport paths.

    Returns ``(path, is_absolute)``. System routes (``/api/health``, ``/api/version``)
    sit outside the ``/api/v1`` prefix that the httpx client uses as ``base_url``.
    """
    if url.startswith("/api/") and not url.startswith(_API_V1_PREFIX):
        origin = _api_root_origin(str(http_client.base_url))
        if origin:
            return origin + url, True
    if url.startswith(_API_V1_PREFIX):
        path = url[len(_API_V1_PREFIX) :]
        return path if path.startswith("/") else f"/{path}", False
    return url, False


class _HttpxTransportAdapter:
    """Route generated-client httpx calls through :class:`_Transport`."""

    def __init__(self, transport: _Transport) -> None:
        self._transport = transport

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        resolved, absolute = _resolve_generated_url(self._transport._http, url)
        if absolute:
            response = self._transport._http.request(method, resolved, **kwargs)
        else:
            response = self._transport.request_raw(method, resolved, **kwargs)
        return _normalize_no_content_response(response)


class _AsyncHttpxTransportAdapter:
    def __init__(self, transport: _AsyncTransport) -> None:
        self._transport = transport

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        resolved, absolute = _resolve_generated_url(self._transport._http, url)
        if absolute:
            response = await self._transport._http.request(method, resolved, **kwargs)
        else:
            response = await self._transport.request_raw(method, resolved, **kwargs)
        return _normalize_no_content_response(response)


class TransportBackedClient:
    """Minimal AuthenticatedClient stand-in for generated ``sync()`` helpers."""

    raise_on_unexpected_status = False

    def __init__(self, transport: _Transport) -> None:
        self._transport = transport
        self._client = _HttpxTransportAdapter(transport)

    def get_httpx_client(self) -> _HttpxTransportAdapter:
        return self._client


class AsyncTransportBackedClient:
    raise_on_unexpected_status = False

    def __init__(self, transport: _AsyncTransport) -> None:
        self._transport = transport
        self._client = _AsyncHttpxTransportAdapter(transport)

    def get_httpx_client(self) -> _AsyncHttpxTransportAdapter:
        return self._client

    def get_async_httpx_client(self) -> _AsyncHttpxTransportAdapter:
        return self._client


def unwrap_generated_response(
    response: Response[Any],
    *,
    method: str = "HTTP",
    path: str = "",
) -> Any:
    """Turn a generated ``sync_detailed`` / ``asyncio_detailed`` response into a result or SDK error."""
    parsed = response.parsed
    if isinstance(parsed, ErrorSchema):
        raise_for_response(
            status_code=int(response.status_code),
            method=method,
            path=path,
            body=parsed.to_dict(),
        )
    if parsed is None:
        if int(response.status_code) in {204, 205}:
            return None
        raise_for_response(
            status_code=int(response.status_code),
            method=method,
            path=path,
            body=error_body_from_response(
                status_code=int(response.status_code),
                content=response.content,
                content_type=response.headers.get("content-type", ""),
            ),
        )
    return parsed


def call_generated_sync(detailed_fn: Any, *args: Any, client: TransportBackedClient, **kwargs: Any) -> Any:
    return unwrap_generated_response(detailed_fn(*args, client=client, **kwargs))


async def call_generated_async(detailed_fn: Any, *args: Any, client: AsyncTransportBackedClient, **kwargs: Any) -> Any:
    return unwrap_generated_response(await detailed_fn(*args, client=client, **kwargs))
