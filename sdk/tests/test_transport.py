"""Tests for _Transport: retry logic, error mapping, auth injection."""

import httpx
import pytest

from ocmo.client import OcmoClient, _Transport, _VersionChecker
from ocmo.config import OcmoConfig
from ocmo.errors import (
    OcmoAuthError,
    OcmoNotFoundError,
    OcmoValidationError,
)

SERVER = "https://ocmo.example.com"


def _cfg(**kwargs) -> OcmoConfig:
    base = dict(server=SERVER, retries=2)
    base.update(kwargs)
    return OcmoConfig(**base)  # type: ignore[arg-type]


def _transport(cfg: OcmoConfig) -> _Transport:
    import httpx

    http = httpx.Client(base_url=cfg.base_url)
    checker = _VersionChecker("0.8.19", cfg.server)
    checker._checked = True  # skip version check
    return _Transport(http, None, cfg.retries, checker)


# ---------------------------------------------------------------------------
# Error status mapping
# ---------------------------------------------------------------------------


def test_404_raises_not_found(respx_mock):
    respx_mock.get(f"{SERVER}/api/v1/test").mock(return_value=httpx.Response(404, json={"error": "not found"}))
    cfg = _cfg()
    t = _transport(cfg)
    with pytest.raises(OcmoNotFoundError):
        t.request("GET", "/test")


def test_422_raises_validation(respx_mock):
    respx_mock.get(f"{SERVER}/api/v1/test").mock(return_value=httpx.Response(422, json={"error": "bad input"}))
    cfg = _cfg()
    t = _transport(cfg)
    with pytest.raises(OcmoValidationError):
        t.request("GET", "/test")


def test_non_json_error_body(respx_mock):
    respx_mock.get(f"{SERVER}/api/v1/test").mock(return_value=httpx.Response(500, content=b"Internal Server Error"))
    cfg = _cfg()
    t = _transport(cfg)
    from ocmo.errors import OcmoAPIError

    with pytest.raises(OcmoAPIError, match="Internal Server Error"):
        t.request("GET", "/test")


def test_html_404_error_body(respx_mock):
    html = (
        "<!DOCTYPE html><html><head>"
        "<title>Page not found at /api/v1/ns/prod/~resolve/</title>"
        "</head><body><h1>Not Found</h1></body></html>"
    )
    respx_mock.get(f"{SERVER}/api/v1/test").mock(
        return_value=httpx.Response(
            404,
            content=html.encode(),
            headers={"content-type": "text/html; charset=utf-8"},
        )
    )
    cfg = _cfg()
    t = _transport(cfg)
    with pytest.raises(OcmoNotFoundError, match="Not found: /api/v1/ns/prod/~resolve/"):
        t.request("GET", "/test")


# ---------------------------------------------------------------------------
# Retries
# ---------------------------------------------------------------------------


def test_get_retried_on_503(respx_mock):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return httpx.Response(503, json={"error": "unavailable"})
        return httpx.Response(200, json={"ok": True})

    respx_mock.get(f"{SERVER}/api/v1/test").mock(side_effect=handler)
    cfg = _cfg(retries=3)
    t = _transport(cfg)
    resp = t.request("GET", "/test")
    assert resp.status_code == 200
    assert call_count == 3


def test_post_not_retried(respx_mock):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(503, json={"error": "unavailable"})

    respx_mock.post(f"{SERVER}/api/v1/test").mock(side_effect=handler)
    cfg = _cfg(retries=3)
    t = _transport(cfg)
    from ocmo.errors import OcmoAPIError

    with pytest.raises(OcmoAPIError):
        t.request("POST", "/test")
    assert call_count == 1  # POST must not be retried


# ---------------------------------------------------------------------------
# 401 handling
# ---------------------------------------------------------------------------


def test_401_raises_auth_error(respx_mock):
    respx_mock.get(f"{SERVER}/api/v1/test").mock(return_value=httpx.Response(401, json={"detail": "Not authenticated"}))
    cfg = _cfg()
    t = _transport(cfg)
    with pytest.raises(OcmoAuthError):
        t.request("GET", "/test")


# ---------------------------------------------------------------------------
# Full client resolve smoke test
# ---------------------------------------------------------------------------


def test_client_resolve_builds_url(respx_mock):
    respx_mock.get(f"{SERVER}/api/v1/ns/prod/~resolve/app/web").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [{"name": "app.json", "version": 1, "format": "json", "url": None}],
                "length": 1,
                "trace_only": False,
            },
        )
    )
    # Skip version check
    respx_mock.get(f"{SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "0.8.19"}))
    cfg = _cfg()
    with OcmoClient(config=cfg) as client:
        result = client.ns("prod").resolve("app/web")
    assert len(result) == 1
    assert result["app.json"].name == "app.json"


def test_client_resolve_python_cast(respx_mock):
    """python cast must send json on wire but return python in result.cast."""

    def check_wire(req: httpx.Request) -> httpx.Response:
        assert "cast=json" in str(req.url)
        return httpx.Response(
            200,
            json={
                "items": [{"name": "a.json", "version": 1, "format": "json", "url": None}],
                "length": 1,
            },
        )

    respx_mock.get(f"{SERVER}/api/v1/ns/prod/~resolve/app").mock(side_effect=check_wire)
    respx_mock.get(f"{SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "0.8.19"}))
    cfg = _cfg()
    with OcmoClient(config=cfg) as client:
        result = client.ns("prod").resolve("app", cast="python")
    assert result.cast == "python"
    assert result.wire_cast == "json"
