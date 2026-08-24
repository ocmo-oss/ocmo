"""Additional coverage for resolve.py — resolver config, save, prefetch, async."""

from __future__ import annotations

import httpx
import pytest

from ocmo.errors import NoArtifactError, UnstructuredFormatError
from ocmo.resolve import (
    AsyncResolvedItem,
    ResolvedItem,
    ResolverConfig,
    ResolverHooks,
    build_async_resolve_result,
    build_resolve_result,
)

SERVER = "https://ocmo.example.com"


def _item(
    name: str = "app.json",
    fmt: str = "json",
    url: str | None = None,
    checksum: str | None = None,
    trace_only: bool = False,
) -> ResolvedItem:
    return ResolvedItem(
        name=name,
        version=1,
        format=fmt,
        url=url,
        checksum=checksum,
        trace={},
        trace_only=trace_only,
        http=httpx.Client(),
        server_origin=SERVER,
    )


def _async_item(
    name: str = "app.json",
    fmt: str = "json",
    url: str | None = None,
    trace_only: bool = False,
) -> AsyncResolvedItem:
    return AsyncResolvedItem(
        name=name,
        version=1,
        format=fmt,
        url=url,
        checksum=None,
        trace={},
        trace_only=trace_only,
        http=httpx.AsyncClient(),
        server_origin=SERVER,
    )


# ---------------------------------------------------------------------------
# ResolverHooks
# ---------------------------------------------------------------------------


def test_resolver_hooks_properties():
    hooks = ResolverHooks(
        {
            "validate": "echo validate",
            "validate_all": "echo validate_all",
            "post_resolve": "echo post",
            "post_resolve_all": "echo post_all",
        }
    )
    assert hooks.validate == "echo validate"
    assert hooks.validate_all == "echo validate_all"
    assert hooks.post_resolve == "echo post"
    assert hooks.post_resolve_all == "echo post_all"


def test_resolver_hooks_missing_returns_none():
    hooks = ResolverHooks({})
    assert hooks.validate is None
    assert hooks.post_resolve_all is None


def test_resolver_hooks_repr():
    hooks = ResolverHooks({"validate": "cmd"})
    assert "validate" in repr(hooks)


# ---------------------------------------------------------------------------
# ResolverConfig
# ---------------------------------------------------------------------------


def test_resolver_config_properties():
    rc = ResolverConfig(
        {
            "cast": "json",
            "parameters": {"env": "prod"},
            "hooks": {"validate": "echo v"},
        }
    )
    assert rc.cast == "json"
    assert rc.parameters == {"env": "prod"}
    assert rc.hooks.validate == "echo v"


def test_resolver_config_empty_parameters():
    rc = ResolverConfig({})
    assert rc.parameters == {}
    assert rc.cast is None


def test_resolver_config_repr():
    rc = ResolverConfig({"cast": "yaml"})
    assert "yaml" in repr(rc)


# ---------------------------------------------------------------------------
# ResolveResult with resolver
# ---------------------------------------------------------------------------


def test_result_with_resolver_config():
    result = build_resolve_result(
        {
            "items": [],
            "length": 0,
            "resolver": {"cast": "json", "parameters": {"k": "v"}, "hooks": {}},
        },
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status="miss",
    )
    assert result.resolver is not None
    assert result.resolver.cast == "json"


def test_result_without_resolver_is_none():
    result = build_resolve_result(
        {"items": [], "length": 0},
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    assert result.resolver is None


def test_result_repr():
    result = build_resolve_result(
        {"items": [], "length": 0},
        http=httpx.Client(),
        server_origin=SERVER,
        cast="json",
        cache_status="hit",
    )
    r = repr(result)
    assert "hit" in r
    assert "json" in r


# ---------------------------------------------------------------------------
# ResolvedItem.save
# ---------------------------------------------------------------------------


def test_item_save(tmp_path, respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"saved-data"))

    item = _item(url=url)
    dest = tmp_path / "out.json"
    item.save(dest)
    assert dest.read_bytes() == b"saved-data"


def test_item_save_creates_parents(tmp_path, respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"data"))

    item = _item(url=url)
    dest = tmp_path / "sub" / "dir" / "out.json"
    item.save(dest, create_parents=True)
    assert dest.read_bytes() == b"data"


# ---------------------------------------------------------------------------
# ResolveResult.prefetch
# ---------------------------------------------------------------------------


def test_prefetch_downloads_all(tmp_path, respx_mock):
    urls = [f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok{i}" for i in range(3)]
    for i, url in enumerate(urls):
        respx_mock.get(url).mock(return_value=httpx.Response(200, content=f"data{i}".encode()))

    result = build_resolve_result(
        {
            "items": [{"name": f"f{i}.json", "version": 1, "format": "json", "url": urls[i]} for i in range(3)],
            "length": 3,
        },
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    result.prefetch(max_workers=2)
    for i in range(3):
        assert result[f"f{i}.json"]._bytes == f"data{i}".encode()


# ---------------------------------------------------------------------------
# Structured access on resolved items
# ---------------------------------------------------------------------------


def test_json_item_structured_access(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b'{"host": "db", "port": 5432}'))

    item = _item(url=url, fmt="json")
    assert item.get("host") == "db"
    assert item.get("port") == 5432
    assert "host" in item


def test_raw_item_structured_access_raises(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"raw"))

    item = _item(url=url, fmt="raw")
    with pytest.raises(UnstructuredFormatError):
        _ = item.data


# ---------------------------------------------------------------------------
# AsyncResolvedItem
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_item_get_bytes(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"async-data"))

    item = AsyncResolvedItem(
        name="app.json",
        version=1,
        format="json",
        url=url,
        checksum=None,
        trace={},
        trace_only=False,
        http=httpx.AsyncClient(),
        server_origin=SERVER,
    )
    data = await item.get_bytes()
    assert data == b"async-data"


@pytest.mark.asyncio
async def test_async_item_trace_only_raises():
    item = _async_item(trace_only=True)
    with pytest.raises(NoArtifactError):
        await item.get_bytes()


@pytest.mark.asyncio
async def test_async_item_memoised(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"once"))

    item = AsyncResolvedItem(
        name="app.json",
        version=1,
        format="json",
        url=url,
        checksum=None,
        trace={},
        trace_only=False,
        http=httpx.AsyncClient(),
        server_origin=SERVER,
    )
    await item.get_bytes()
    await item.get_bytes()
    assert respx_mock.calls.call_count == 1


# ---------------------------------------------------------------------------
# AsyncResolveResult
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_result_prefetch(respx_mock):
    urls = [f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok{i}" for i in range(2)]
    for i, url in enumerate(urls):
        respx_mock.get(url).mock(return_value=httpx.Response(200, content=f"d{i}".encode()))

    result = build_async_resolve_result(
        {
            "items": [{"name": f"f{i}.json", "version": 1, "format": "json", "url": urls[i]} for i in range(2)],
            "length": 2,
        },
        http=httpx.AsyncClient(),
        server_origin=SERVER,
        cast=None,
        cache_status="miss",
    )
    await result.prefetch()
    assert respx_mock.calls.call_count == 2


def test_async_result_getitem():
    result = build_async_resolve_result(
        {"items": [{"name": "a.json", "version": 1, "format": "json", "url": None}], "length": 1},
        http=httpx.AsyncClient(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    assert result["a.json"].name == "a.json"


def test_async_result_missing_key():
    result = build_async_resolve_result(
        {"items": [], "length": 0},
        http=httpx.AsyncClient(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    with pytest.raises(KeyError):
        _ = result["missing"]


def test_async_result_len():
    result = build_async_resolve_result(
        {
            "items": [
                {"name": "a.json", "version": 1, "format": "json", "url": None},
                {"name": "b.json", "version": 1, "format": "json", "url": None},
            ],
            "length": 2,
        },
        http=httpx.AsyncClient(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    assert len(result) == 2


def test_async_result_repr():
    result = build_async_resolve_result(
        {"items": [], "length": 0},
        http=httpx.AsyncClient(),
        server_origin=SERVER,
        cast=None,
        cache_status="hit",
    )
    assert "hit" in repr(result)


# ---------------------------------------------------------------------------
# Additional coverage: uncovered paths
# ---------------------------------------------------------------------------


def test_item_url_none_no_trace_only_raises():
    """url=None and trace_only=False must raise NoArtifactError."""
    item = _item(url=None, trace_only=False)
    with pytest.raises(NoArtifactError):
        _ = item.bytes


def test_item_text_property(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"hello"))

    item = _item(url=url)
    assert item.text == "hello"


def test_item_http_error_raises_artifact_expired(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(side_effect=httpx.ConnectError("refused"))

    item = _item(url=url)
    from ocmo.errors import ArtifactExpiredError

    with pytest.raises(ArtifactExpiredError):
        _ = item.bytes


def test_item_401_raises_artifact_expired(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(401))

    item = _item(url=url)
    from ocmo.errors import ArtifactExpiredError

    with pytest.raises(ArtifactExpiredError, match="401"):
        _ = item.bytes


def test_checksum_no_prefix_uses_sha256(respx_mock):
    """Checksum without 'algo:' prefix defaults to sha256."""
    import hashlib

    data = b"payload"
    digest = hashlib.sha256(data).hexdigest()
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=data))

    item = _item(url=url, checksum=digest)  # no "sha256:" prefix
    assert item.bytes == data


def test_item_open(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"stream"))

    item = _item(url=url)
    collected = b""
    with item.open() as resp:
        for chunk in resp.iter_bytes():
            collected += chunk
    assert collected == b"stream"


def test_apply_python_cast_with_bytes():
    """_apply_python_cast must parse pre-fetched bytes into Python objects."""
    from ocmo.resolve import _apply_python_cast

    result = build_resolve_result(
        {"items": [{"name": "a.json", "version": 1, "format": "json", "url": None}], "length": 1},
        http=httpx.Client(),
        server_origin=SERVER,
        cast="python",
        cache_status=None,
    )
    result._items[0]._bytes = b'{"key": "value"}'
    _apply_python_cast(result)
    from ocmo.structured import _SENTINEL

    assert result._items[0]._parsed_data != _SENTINEL


def test_save_all_writes_nested_path(tmp_path, respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"nested"))

    result = build_resolve_result(
        {"items": [{"name": "subdir/app.json", "version": 1, "format": "json", "url": url}], "length": 1},
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    result.save_all(tmp_path)
    assert (tmp_path / "subdir" / "app.json").read_bytes() == b"nested"


@pytest.mark.asyncio
async def test_async_item_text_async(respx_mock):
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"hello async"))

    item = AsyncResolvedItem(
        name="app.json",
        version=1,
        format="json",
        url=url,
        checksum=None,
        trace={},
        trace_only=False,
        http=httpx.AsyncClient(),
        server_origin=SERVER,
    )
    text = await item.text_async()
    assert text == "hello async"


@pytest.mark.asyncio
async def test_async_item_wrong_origin():
    item = _async_item(url="https://evil.example.com/artifact")
    with pytest.raises(ValueError, match="origin"):
        await item.get_bytes()


def test_async_result_items_property():
    result = build_async_resolve_result(
        {"items": [{"name": "a.json", "version": 1, "format": "json", "url": None}], "length": 1},
        http=httpx.AsyncClient(),
        server_origin=SERVER,
        cast=None,
        cache_status="cast",
    )
    assert len(result.items) == 1
    assert result.cache_status == "cast"


def test_result_items_property():
    result = build_resolve_result(
        {"items": [{"name": "a.json", "version": 1, "format": "json", "url": None}], "length": 1},
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    assert len(result.items) == 1


def test_result_root():
    result = build_resolve_result(
        {
            "items": [],
            "length": 0,
            "root": {"path": "app/web", "version": 5},
        },
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    assert result.root == {"path": "app/web", "version": 5}


def test_result_iteration():
    result = build_resolve_result(
        {"items": [{"name": "a.json", "version": 1, "format": "json", "url": None}], "length": 1},
        http=httpx.Client(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    names = [item.name for item in result]
    assert names == ["a.json"]


def test_async_result_iteration():
    result = build_async_resolve_result(
        {"items": [{"name": "a.json", "version": 1, "format": "json", "url": None}], "length": 1},
        http=httpx.AsyncClient(),
        server_origin=SERVER,
        cast=None,
        cache_status=None,
    )
    # __aiter__ returns a regular iterator for sync access
    items = list(result.__aiter__())
    assert len(items) == 1


def test_async_item_repr():
    item = _async_item()
    assert "app.json" in repr(item)


@pytest.mark.asyncio
async def test_async_item_get_bytes_memoised_fast_path(respx_mock):
    """Ensure the cached bytes branch is hit."""
    url = f"{SERVER}/api/v1/ns/prod/~resolve/app/~download/tok"
    respx_mock.get(url).mock(return_value=httpx.Response(200, content=b"cached"))

    item = AsyncResolvedItem(
        name="app.json",
        version=1,
        format="json",
        url=url,
        checksum=None,
        trace={},
        trace_only=False,
        http=httpx.AsyncClient(),
        server_origin=SERVER,
    )
    first = await item.get_bytes()
    second = await item.get_bytes()  # hits _bytes is not None branch
    assert first == second == b"cached"
