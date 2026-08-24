"""Tests for credential providers and token cache."""

import stat
import time

import httpx
import pytest

from ocmo.auth import (
    _BearerProvider,
    _cache_key,
    _fetch_token,
    _OIDCProvider,
    _OIDCTokenCache,
    _read_cache,
    _ResolverTokenProvider,
    _write_cache,
    build_provider,
)
from ocmo.config import OcmoConfig
from ocmo.errors import OcmoAuthError, OcmoConfigError


def _cfg(**kwargs) -> OcmoConfig:
    base = dict(server="https://ocmo.example.com")
    base.update(kwargs)
    return OcmoConfig(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------


def test_cache_key_deterministic():
    k1 = _cache_key("https://idp", "svc", "api", "openid", "client_credentials")
    k2 = _cache_key("https://idp", "svc", "api", "openid", "client_credentials")
    assert k1 == k2


def test_cache_key_varies_by_input():
    k1 = _cache_key("https://idp", "svc", "api", "openid", "client_credentials")
    k2 = _cache_key("https://idp", "svc2", "api", "openid", "client_credentials")
    assert k1 != k2


def test_cache_key_varies_by_grant_type():
    k1 = _cache_key("https://idp", "svc", "api", "openid", "client_credentials")
    k2 = _cache_key("https://idp", "svc", "api", "openid", "password", "user@example.com")
    assert k1 != k2


def test_cache_key_varies_by_auth_profile():
    base = ("https://idp", "svc", "api", "openid", "client_credentials")
    k1 = _cache_key(*base, auth_profile="alice")
    k2 = _cache_key(*base, auth_profile="bob")
    assert k1 != k2


# ---------------------------------------------------------------------------
# Disk cache read/write
# ---------------------------------------------------------------------------


def test_write_and_read_cache(tmp_path):
    _write_cache(tmp_path, "key", {"access_token": "tok", "expires_at": 9999999999.0})
    result = _read_cache(tmp_path, "key")
    assert result is not None
    assert result["access_token"] == "tok"


def test_cache_file_has_0600_perms(tmp_path):
    _write_cache(tmp_path, "key", {"access_token": "tok", "expires_at": 9999999999.0})
    path = tmp_path / "key"
    mode = path.stat().st_mode
    assert not (mode & (stat.S_IRGRP | stat.S_IRWXO))


def test_read_missing_cache_returns_none(tmp_path):
    assert _read_cache(tmp_path, "nonexistent") is None


# ---------------------------------------------------------------------------
# _OIDCTokenCache
# ---------------------------------------------------------------------------


def test_token_cache_returns_none_when_empty(tmp_path):
    cache = _OIDCTokenCache(tmp_path, "https://idp", "svc", None, "openid", "client_credentials")
    assert cache.get() is None


def test_token_cache_returns_valid_token(tmp_path):
    cache = _OIDCTokenCache(tmp_path, "https://idp", "svc", None, "openid", "client_credentials")
    cache.set("mytoken", 3600)
    assert cache.get() == "mytoken"


def test_token_cache_expired(tmp_path):
    cache = _OIDCTokenCache(tmp_path, "https://idp", "svc", None, "openid", "client_credentials")
    cache._token = "expired"
    cache._expires_at = time.time() - 1  # already expired
    assert cache.get() is None


# ---------------------------------------------------------------------------
# _fetch_token
# ---------------------------------------------------------------------------


def test_fetch_token_success(respx_mock):
    respx_mock.post("https://idp.example.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok123", "expires_in": 3600})
    )
    token, expires = _fetch_token("https://idp.example.com/token", "svc", "secret", "openid", None)
    assert token == "tok123"
    assert expires == 3600


def test_fetch_token_non_200_raises(respx_mock):
    respx_mock.post("https://idp.example.com/token").mock(
        return_value=httpx.Response(401, json={"error": "invalid_client"})
    )
    with pytest.raises(OcmoAuthError):
        _fetch_token("https://idp.example.com/token", "svc", "secret", "openid", None)


def test_fetch_token_with_audience(respx_mock):
    def check_audience(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        assert "audience=myapi" in body
        return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})

    respx_mock.post("https://idp.example.com/token").mock(side_effect=check_audience)
    _fetch_token("https://idp.example.com/token", "svc", "secret", "openid", "myapi")


def test_fetch_token_password_grant(respx_mock):
    def check_password_grant(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        assert "grant_type=password" in body
        assert "username=admin%40example.com" in body
        assert "password=secret" in body
        return httpx.Response(200, json={"access_token": "pw-tok", "expires_in": 3600})

    respx_mock.post("https://idp.example.com/token").mock(side_effect=check_password_grant)
    token, expires = _fetch_token(
        "https://idp.example.com/token",
        "ocmo-sdk",
        "client-secret",
        "openid profile email groups",
        None,
        grant_type="password",
        username="admin@example.com",
        password="secret",
    )
    assert token == "pw-tok"
    assert expires == 3600


def test_fetch_token_password_grant_requires_credentials():
    with pytest.raises(OcmoConfigError, match="OCMO_OIDC_USERNAME"):
        _fetch_token(
            "https://idp.example.com/token",
            "ocmo-sdk",
            "client-secret",
            "openid",
            None,
            grant_type="password",
        )


def test_oidc_provider_password_grant_requires_username(tmp_path):
    with pytest.raises(OcmoConfigError, match="OCMO_OIDC_USERNAME"):
        _OIDCProvider(
            _cfg(
                auth_mode="oidc",
                client_id="ocmo-sdk",
                client_secret="s",
                oidc_grant_type="password",
                cache_dir=tmp_path,
            )
        )


def test_fetch_token_missing_access_token_raises(respx_mock):
    respx_mock.post("https://idp.example.com/token").mock(
        return_value=httpx.Response(200, json={"token_type": "Bearer"})
    )
    with pytest.raises(OcmoAuthError, match="access_token"):
        _fetch_token("https://idp.example.com/token", "svc", "secret", "openid", None)


# ---------------------------------------------------------------------------
# _OIDCProvider
# ---------------------------------------------------------------------------


def test_oidc_provider_requires_client_id():
    with pytest.raises(OcmoConfigError, match="OCMO_CLIENT_ID"):
        _OIDCProvider(_cfg(auth_mode="oidc", client_secret="s"))


def test_oidc_provider_requires_client_secret():
    with pytest.raises(OcmoConfigError, match="OCMO_CLIENT_SECRET"):
        _OIDCProvider(_cfg(auth_mode="oidc", client_id="svc"))


def test_oidc_provider_allows_cached_token_without_secret(tmp_path):
    from ocmo.auth import store_oidc_access_token

    cfg = _cfg(
        auth_mode="oidc",
        client_id="ocmo-api",
        oidc_issuer="https://idp.example.com",
        cache_dir=tmp_path,
    )
    store_oidc_access_token(cfg, "device-tok", 3600)
    provider = _OIDCProvider(cfg)
    assert provider.get_token() == "device-tok"


def test_oidc_provider_get_token_uses_cache(tmp_path, respx_mock):
    respx_mock.post("https://idp.example.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
    )
    cfg = _cfg(
        auth_mode="oidc",
        client_id="svc",
        client_secret="s",
        oidc_token_url="https://idp.example.com/token",
        cache_dir=tmp_path,
    )
    provider = _OIDCProvider(cfg)
    t1 = provider.get_token()
    t2 = provider.get_token()  # must use cache
    assert t1 == t2 == "tok"
    assert respx_mock.calls.call_count == 1


def test_oidc_provider_refresh_re_fetches(tmp_path, respx_mock):
    respx_mock.post("https://idp.example.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "newtok", "expires_in": 3600})
    )
    cfg = _cfg(
        auth_mode="oidc",
        client_id="svc",
        client_secret="s",
        oidc_token_url="https://idp.example.com/token",
        cache_dir=tmp_path,
    )
    provider = _OIDCProvider(cfg)
    _ = provider.get_token()
    _ = provider.refresh()
    assert respx_mock.calls.call_count == 2


def test_oidc_provider_inject_headers(tmp_path, respx_mock):
    respx_mock.post("https://idp.example.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "bearer-tok", "expires_in": 3600})
    )
    cfg = _cfg(
        auth_mode="oidc",
        client_id="svc",
        client_secret="s",
        oidc_token_url="https://idp.example.com/token",
        cache_dir=tmp_path,
    )
    provider = _OIDCProvider(cfg)
    headers: dict[str, str] = {}
    provider.inject_headers(headers)
    assert headers["Authorization"] == "Bearer bearer-tok"


# ---------------------------------------------------------------------------
# _ResolverTokenProvider
# ---------------------------------------------------------------------------


def test_resolver_token_injects_header():
    provider = _ResolverTokenProvider("ocmort-abc123")
    headers: dict[str, str] = {}
    provider.inject_headers(headers)
    assert headers["X-Ocmo-Resolver-Token"] == "ocmort-abc123"


def test_resolver_token_not_in_authorization():
    provider = _ResolverTokenProvider("ocmort-abc123")
    headers: dict[str, str] = {}
    provider.inject_headers(headers)
    assert "Authorization" not in headers


def test_resolver_token_allowed_path():
    provider = _ResolverTokenProvider("ocmort-abc123")
    provider.check_path_allowed("/ns/prod/~resolve/app/web")  # should not raise


def test_resolver_token_rejected_path():
    from ocmo.errors import OcmoAuthError

    provider = _ResolverTokenProvider("ocmort-abc123")
    with pytest.raises(OcmoAuthError, match="OIDC"):
        provider.check_path_allowed("/ns/prod/configs")


def test_resolver_token_requires_token():
    with pytest.raises(OcmoConfigError):
        _ResolverTokenProvider("")


# ---------------------------------------------------------------------------
# _BearerProvider
# ---------------------------------------------------------------------------


def test_bearer_injects_authorization():
    provider = _BearerProvider("my-bearer")
    headers: dict[str, str] = {}
    provider.inject_headers(headers)
    assert headers["Authorization"] == "Bearer my-bearer"


def test_bearer_refresh_from_file(tmp_path):
    token_file = tmp_path / "token.txt"
    token_file.write_text("new-token\n")
    provider = _BearerProvider("old-token", str(token_file))
    changed = provider.refresh_from_file()
    assert changed
    headers: dict[str, str] = {}
    provider.inject_headers(headers)
    assert headers["Authorization"] == "Bearer new-token"


def test_bearer_refresh_from_file_no_file():
    provider = _BearerProvider("tok")
    assert not provider.refresh_from_file()


# ---------------------------------------------------------------------------
# build_provider
# ---------------------------------------------------------------------------


def test_build_provider_none_mode():
    cfg = _cfg(auth_mode="none")
    assert build_provider(cfg) is None


def test_build_provider_bearer():
    cfg = _cfg(auth_mode="bearer", token="bearertok")
    provider = build_provider(cfg)
    assert isinstance(provider, _BearerProvider)


def test_build_provider_resolver_token():
    cfg = _cfg(auth_mode="resolver-token", token="ocmort-abc")
    provider = build_provider(cfg)
    assert isinstance(provider, _ResolverTokenProvider)


def test_build_provider_oidc(tmp_path):
    cfg = _cfg(
        auth_mode="oidc",
        client_id="svc",
        client_secret="s",
        oidc_token_url="https://idp/token",
        cache_dir=tmp_path,
    )
    provider = build_provider(cfg)
    assert isinstance(provider, _OIDCProvider)
