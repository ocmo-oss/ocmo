"""Additional auth coverage: disk cache edge cases, OIDC discovery, client TLS options."""

import httpx
import pytest

from ocmo.auth import (
    _BearerProvider,
    _fetch_oidc_discovery,
    _fetch_token,
    _OIDCProvider,
    _OIDCTokenCache,
    _read_cache,
    _safe_makedirs,
    _write_cache,
    build_provider,
)
from ocmo.client import OcmoClient, _build_httpx_client
from ocmo.config import OcmoConfig
from ocmo.errors import OcmoAuthError, OcmoConfigError


def _cfg(**kwargs) -> OcmoConfig:
    base = dict(server="https://ocmo.example.com")
    base.update(kwargs)
    return OcmoConfig(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _safe_makedirs — insecure directory
# ---------------------------------------------------------------------------


def test_safe_makedirs_creates_directory(tmp_path):
    d = tmp_path / "newcache"
    _safe_makedirs(d)
    assert d.exists()
    assert d.is_dir()


# ---------------------------------------------------------------------------
# Insecure cache file permissions
# ---------------------------------------------------------------------------


def test_read_cache_rejects_world_readable(tmp_path):
    path = tmp_path / "key"
    path.write_text('{"access_token": "x", "expires_at": 9999999999.0}')
    path.chmod(0o644)  # world-readable
    result = _read_cache(tmp_path, "key")
    assert result is None


# ---------------------------------------------------------------------------
# Disk cache returns valid token on cold start
# ---------------------------------------------------------------------------


def test_disk_cache_cold_start(tmp_path):
    import time

    _write_cache(
        tmp_path,
        "key",
        {
            "access_token": "disk-tok",
            "expires_at": time.time() + 3600,
        },
    )
    cache = _OIDCTokenCache(tmp_path, "", "", None, "", "client_credentials")
    cache._key = "key"
    assert cache.get() == "disk-tok"


# ---------------------------------------------------------------------------
# _fetch_oidc_discovery
# ---------------------------------------------------------------------------


def test_fetch_oidc_discovery_success(respx_mock):
    respx_mock.get("https://idp.example.com/.well-known/openid-configuration").mock(
        return_value=httpx.Response(200, json={"token_endpoint": "https://idp.example.com/token"})
    )
    result = _fetch_oidc_discovery("https://idp.example.com")
    assert result["token_endpoint"] == "https://idp.example.com/token"


def test_fetch_oidc_discovery_failure(respx_mock):
    respx_mock.get("https://idp.example.com/.well-known/openid-configuration").mock(return_value=httpx.Response(500))
    with pytest.raises(OcmoAuthError, match="discovery"):
        _fetch_oidc_discovery("https://idp.example.com")


# ---------------------------------------------------------------------------
# OIDCProvider discovers issuer from api_version_info
# ---------------------------------------------------------------------------


def test_oidc_provider_discovers_from_api_info(tmp_path, respx_mock):
    respx_mock.get("https://idp.example.com/.well-known/openid-configuration").mock(
        return_value=httpx.Response(200, json={"token_endpoint": "https://idp.example.com/token"})
    )
    respx_mock.post("https://idp.example.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
    )
    cfg = _cfg(auth_mode="oidc", client_id="svc", client_secret="s", cache_dir=tmp_path)
    provider = _OIDCProvider(cfg)
    api_info = {"auth": {"oidc": {"issuer": "https://idp.example.com"}}}
    token = provider.get_token(api_info)
    assert token == "tok"


def test_oidc_provider_no_issuer_raises(tmp_path):
    cfg = _cfg(auth_mode="oidc", client_id="svc", client_secret="s", cache_dir=tmp_path)
    provider = _OIDCProvider(cfg)
    with pytest.raises(OcmoConfigError, match="OCMO_OIDC_ISSUER"):
        provider.get_token()


def test_oidc_provider_missing_token_endpoint(tmp_path, respx_mock):
    respx_mock.get("https://idp.example.com/.well-known/openid-configuration").mock(
        return_value=httpx.Response(200, json={"issuer": "https://idp.example.com"})
    )
    cfg = _cfg(
        auth_mode="oidc",
        client_id="svc",
        client_secret="s",
        oidc_issuer="https://idp.example.com",
        cache_dir=tmp_path,
    )
    provider = _OIDCProvider(cfg)
    with pytest.raises(OcmoConfigError, match="token_endpoint"):
        provider.get_token()


# ---------------------------------------------------------------------------
# httpx client construction with TLS options
# ---------------------------------------------------------------------------


def test_ca_bundle_stored_in_config(tmp_path):
    bundle = tmp_path / "ca.pem"
    bundle.write_text("fake-ca")
    cfg = _cfg(ca_bundle=str(bundle))
    assert cfg.ca_bundle == str(bundle)


def test_insecure_skip_verify_builds_client():
    with pytest.warns(UserWarning):
        cfg = _cfg(insecure_skip_tls_verify=True)
    http = _build_httpx_client(cfg)
    http.close()


# ---------------------------------------------------------------------------
# client.version_info
# ---------------------------------------------------------------------------


def test_client_version_info(respx_mock):
    respx_mock.get("https://ocmo.example.com/api/version").mock(
        return_value=httpx.Response(200, json={"version": "0.8.19", "product": "ocmo"})
    )
    with OcmoClient(config=_cfg()) as client:
        info = client.version_info()
    assert info is not None
    assert info["version"] == "0.8.19"


# ---------------------------------------------------------------------------
# client.close explicit
# ---------------------------------------------------------------------------


def test_client_close():
    client = OcmoClient(config=_cfg())
    client.close()  # must not raise


# ---------------------------------------------------------------------------
# build_provider edge cases
# ---------------------------------------------------------------------------


def test_build_provider_resolver_token_no_token():
    cfg = _cfg(auth_mode="resolver-token", token=None)
    with pytest.raises(OcmoConfigError, match="OCMO_TOKEN"):
        build_provider(cfg)


def test_build_provider_bearer_no_token():
    cfg = _cfg(auth_mode="bearer", token=None)
    with pytest.raises(OcmoConfigError, match="OCMO_TOKEN"):
        build_provider(cfg)


# ---------------------------------------------------------------------------
# _BearerProvider empty token
# ---------------------------------------------------------------------------


def test_bearer_empty_token_raises():
    with pytest.raises(OcmoConfigError, match="OCMO_TOKEN"):
        _BearerProvider("")


def test_bearer_refresh_from_file_same_token(tmp_path):
    token_file = tmp_path / "tok"
    token_file.write_text("same-token")
    provider = _BearerProvider("same-token", str(token_file))
    changed = provider.refresh_from_file()
    assert not changed  # same value — no change


def test_bearer_refresh_from_file_oserror(tmp_path):
    provider = _BearerProvider("tok", "/nonexistent/path/token.txt")
    changed = provider.refresh_from_file()
    assert not changed  # OSError handled gracefully


# ---------------------------------------------------------------------------
# _fetch_token network error
# ---------------------------------------------------------------------------


def test_fetch_token_network_error(respx_mock):
    respx_mock.post("https://idp.example.com/token").mock(side_effect=httpx.ConnectError("Connection refused"))
    with pytest.raises(OcmoAuthError, match="Token endpoint request failed"):
        _fetch_token("https://idp.example.com/token", "svc", "secret", "openid", None)


def test_store_and_invalidate_oidc_token_cache(tmp_path):
    from ocmo.auth import invalidate_oidc_token_cache, oidc_cache_status, store_oidc_access_token

    cfg = _cfg(
        client_id="cli",
        client_secret="secret",
        oidc_issuer="https://idp.example.com",
        cache_dir=tmp_path,
    )
    assert oidc_cache_status(cfg)["cached"] is False
    store_oidc_access_token(cfg, "access-xyz", 3600)
    assert oidc_cache_status(cfg)["cached"] is True
    assert invalidate_oidc_token_cache(cfg) is True
    assert oidc_cache_status(cfg)["cached"] is False
