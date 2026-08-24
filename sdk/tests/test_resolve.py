"""Tests for ResolveResult, ResolvedItem, and save_all path safety."""

import threading

import httpx
import pytest

from ocmo.client import _encode_resolve_path
from ocmo.errors import ChecksumMismatchError, NoArtifactError
from ocmo.resolve import (
    ResolvedItem,
    _safe_join,
    build_resolve_result,
)

SERVER = "https://ocmo.example.com"


def test_encode_resolve_path_escapes_scope_root_dot() -> None:
    assert _encode_resolve_path(".") == "@"
    assert _encode_resolve_path("audit-test/new.conf") == "audit-test/new.conf"


def _make_item(
    name: str = "app.json",
    fmt: str = "json",
    url: str = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok123",
    checksum: str | None = None,
    trace_only: bool = False,
    http: httpx.Client | None = None,
) -> ResolvedItem:
    return ResolvedItem(
        name=name,
        version=1,
        format=fmt,
        url=url,
        checksum=checksum,
        trace={},
        trace_only=trace_only,
        http=http or httpx.Client(),
        server_origin=SERVER,
    )


# ---------------------------------------------------------------------------
# trace_only
# ---------------------------------------------------------------------------


def test_trace_only_raises_no_artifact():
    item = _make_item(trace_only=True)
    with pytest.raises(NoArtifactError, match="trace_only"):
        _ = item.bytes


# ---------------------------------------------------------------------------
# URL origin validation
# ---------------------------------------------------------------------------


def test_artifact_url_wrong_origin_rejected():
    item = _make_item(url="https://evil.example.com/artifact")
    with pytest.raises(ValueError, match="origin"):
        _ = item.bytes


def test_artifact_url_same_host_different_port_normalized(respx_mock):
    """Gateway may return localhost while OCMO_SERVER is localhost:8080."""
    server = "http://localhost:8080"
    url = "http://localhost/api/v1/ns/prod/~resolve/app/~download/tok"
    expected = f"{server}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(expected).mock(return_value=httpx.Response(200, content=b'{"x": 1}'))

    item = ResolvedItem(
        name="app.json",
        version=1,
        format="json",
        url=url,
        checksum=None,
        trace={},
        trace_only=False,
        http=httpx.Client(),
        server_origin=server,
    )
    assert item.bytes == b'{"x": 1}'
    assert respx_mock.calls.call_count == 1


def test_artifact_download_uses_transport():
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    seen: dict[str, str] = {}

    class MockTransport:
        def request_raw(self, method: str, path: str, **kwargs):
            seen["method"] = method
            seen["path"] = path
            return httpx.Response(
                200,
                content=b"via-transport",
                request=httpx.Request(method, path),
            )

        def auth_headers(self, path: str = "") -> dict[str, str]:
            seen["auth_path"] = path
            return {"Authorization": "Bearer test-token"}

    item = ResolvedItem(
        name="app.json",
        version=1,
        format="json",
        url=url,
        checksum=None,
        trace={},
        trace_only=False,
        http=httpx.Client(),
        server_origin=SERVER,
        transport=MockTransport(),
    )
    assert item.bytes == b"via-transport"
    assert seen["method"] == "GET"
    assert seen["path"] == "/ns/prod/~resolve/app/~download/tok"


# ---------------------------------------------------------------------------
# Checksum verification
# ---------------------------------------------------------------------------


def test_checksum_mismatch_raises(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"bad bytes"))

    # respx_mock patches globally; use a regular httpx.Client
    item = _make_item(url=url, checksum="sha256:aaaa")
    with pytest.raises(ChecksumMismatchError):
        _ = item.bytes


def test_checksum_match_ok(respx_mock):
    import hashlib

    data = b'{"key": "value"}'
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=data))

    item = _make_item(url=url, checksum=digest)
    assert item.bytes == data


# ---------------------------------------------------------------------------
# Memoisation / thread safety
# ---------------------------------------------------------------------------


def test_bytes_fetched_once(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"data"))

    item = _make_item(url=url)
    _ = item.bytes
    _ = item.bytes  # second access — must not issue a second request

    assert respx_mock.calls.call_count == 1


def test_concurrent_access_issues_one_request(respx_mock):
    """Multiple threads must only issue one download."""
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"data"))

    item = _make_item(url=url)
    results: list = []

    def _fetch():
        results.append(item.bytes)

    threads = [threading.Thread(target=_fetch) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(r == b"data" for r in results)
    assert respx_mock.calls.call_count == 1


# ---------------------------------------------------------------------------
# save_all path safety (§11)
# ---------------------------------------------------------------------------


def test_safe_join_normal(tmp_path):
    dest = _safe_join(tmp_path, "subdir/app.json")
    assert dest == (tmp_path / "subdir" / "app.json").resolve()


def test_safe_join_absolute_rejected(tmp_path):
    with pytest.raises(ValueError, match="absolute"):
        _safe_join(tmp_path, "/etc/passwd")


def test_safe_join_dotdot_rejected(tmp_path):
    with pytest.raises(ValueError, match=r"\.\."):
        _safe_join(tmp_path, "../escape")


def test_safe_join_normalised_escape_rejected(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        _safe_join(tmp_path, "sub/../../escape")


def test_save_all_refuses_overwrite_by_default(tmp_path):
    existing = tmp_path / "app.json"
    existing.write_bytes(b"old")

    result = build_resolve_result(
        {
            "items": [{"name": "app.json", "version": 1, "format": "json", "url": None}],
            "length": 1,
        },
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    with pytest.raises(FileExistsError, match="overwrite"):
        result.save_all(tmp_path)


def test_save_all_overwrite_allowed(tmp_path, respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"new"))

    existing = tmp_path / "app.json"
    existing.write_bytes(b"old")

    result = build_resolve_result(
        {"items": [{"name": "app.json", "version": 1, "format": "json", "url": url}], "length": 1},
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    result.save_all(tmp_path, overwrite=True)
    assert (tmp_path / "app.json").read_bytes() == b"new"


# ---------------------------------------------------------------------------
# Python cast (§9.4)
# ---------------------------------------------------------------------------


def test_python_cast_translates_to_json(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b'{"x": 1}'))
    http = httpx.Client(transport=respx_mock)

    result = build_resolve_result(
        {"items": [{"name": "app.json", "version": 1, "format": "json", "url": url}], "length": 1},
        http=http,
        server_origin=SERVER,
        cast="python",
        cache_status=None,
    )
    assert result.cast == "python"
    assert result.wire_cast == "json"


# ---------------------------------------------------------------------------
# Iteration / len
# ---------------------------------------------------------------------------


def test_result_len():
    http = httpx.Client()
    result = build_resolve_result(
        {
            "items": [
                {"name": "a.json", "version": 1, "format": "json", "url": None},
                {"name": "b.json", "version": 1, "format": "json", "url": None},
            ],
            "length": 2,
        },
        http=http,
        server_origin=SERVER,
        cast=None,
        cache_status="hit",
    )
    assert len(result) == 2
    assert result.cache_status == "hit"


def test_result_getitem_by_name():
    http = httpx.Client()
    result = build_resolve_result(
        {"items": [{"name": "app.json", "version": 1, "format": "raw", "url": None}], "length": 1},
        http=http,
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    item = result["app.json"]
    assert item.name == "app.json"


def test_result_getitem_missing():
    http = httpx.Client()
    result = build_resolve_result(
        {"items": [], "length": 0},
        http=http,
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    with pytest.raises(KeyError):
        _ = result["missing.json"]
