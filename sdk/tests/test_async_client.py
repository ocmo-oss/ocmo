"""Tests for AsyncOcmoClient and async transport."""

from __future__ import annotations

import httpx
import pytest

from ocmo.client import AsyncOcmoClient
from ocmo.config import OcmoConfig
from ocmo.errors import OcmoConfigError, OcmoNotFoundError

SERVER = "https://ocmo.example.com"


def _cfg(**kwargs) -> OcmoConfig:
    base = dict(server=SERVER, retries=1)
    base.update(kwargs)
    return OcmoConfig(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AsyncOcmoClient construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_client_constructs():
    async with AsyncOcmoClient(config=_cfg()) as client:
        assert client._config.server == SERVER


@pytest.mark.asyncio
async def test_async_client_ns_requires_namespace():
    async with AsyncOcmoClient(config=_cfg()) as client:
        with pytest.raises(OcmoConfigError, match="namespace"):
            client.ns()


@pytest.mark.asyncio
async def test_async_client_ns_uses_default():
    async with AsyncOcmoClient(config=_cfg(namespace="staging")) as client:
        view = client.ns()
        assert view._namespace == "staging"


@pytest.mark.asyncio
async def test_async_client_ns_explicit():
    async with AsyncOcmoClient(config=_cfg()) as client:
        view = client.ns("prod")
        assert view._namespace == "prod"


# ---------------------------------------------------------------------------
# AsyncOcmoClient resolve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_client_resolve(respx_mock):
    respx_mock.get(f"{SERVER}/api/v1/ns/prod/~resolve/app/web").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [{"name": "app.json", "version": 1, "format": "json", "url": None}],
                "length": 1,
            },
        )
    )
    respx_mock.get(f"{SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "0.8.19"}))
    async with AsyncOcmoClient(config=_cfg()) as client:
        result = await client.ns("prod").resolve("app/web")
    assert len(result) == 1
    assert result["app.json"].format == "json"


@pytest.mark.asyncio
async def test_async_client_resolve_python_cast(respx_mock):
    def check(req: httpx.Request) -> httpx.Response:
        assert "cast=json" in str(req.url)
        return httpx.Response(
            200,
            json={
                "items": [{"name": "a.json", "version": 1, "format": "json", "url": None}],
                "length": 1,
            },
        )

    respx_mock.get(f"{SERVER}/api/v1/ns/prod/~resolve/app").mock(side_effect=check)
    respx_mock.get(f"{SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "0.8.19"}))
    async with AsyncOcmoClient(config=_cfg()) as client:
        result = await client.ns("prod").resolve("app", cast="python")
    assert result.cast == "python"
    assert result.wire_cast == "json"


@pytest.mark.asyncio
async def test_async_transport_404_raises(respx_mock):
    respx_mock.get(f"{SERVER}/api/v1/ns/prod/~resolve/app").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )
    respx_mock.get(f"{SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "0.8.19"}))
    async with AsyncOcmoClient(config=_cfg()) as client:
        with pytest.raises(OcmoNotFoundError):
            await client.ns("prod").resolve("app")


@pytest.mark.asyncio
async def test_async_client_version_info(respx_mock):
    respx_mock.get(f"{SERVER}/api/version").mock(
        return_value=httpx.Response(200, json={"version": "0.8.19", "product": "ocmo"})
    )
    async with AsyncOcmoClient(config=_cfg()) as client:
        info = await client.version_info()
    assert info is not None
    assert info["version"] == "0.8.19"


@pytest.mark.asyncio
async def test_async_transport_retries_on_503(respx_mock):
    call_count = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(200, json={"items": [], "length": 0})

    respx_mock.get(f"{SERVER}/api/v1/ns/prod/~resolve/app").mock(side_effect=handler)
    respx_mock.get(f"{SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "0.8.19"}))
    async with AsyncOcmoClient(config=_cfg(retries=2)) as client:
        result = await client.ns("prod").resolve("app")
    assert call_count == 2
    assert len(result) == 0
