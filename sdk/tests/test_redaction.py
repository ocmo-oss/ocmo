"""Security test: credentials must never appear in logs or exceptions (§14, §15)."""

import logging

import pytest

from ocmo.auth import _fetch_token, _ResolverTokenProvider
from ocmo.errors import OcmoAuthError

KNOWN_SECRET = "super-secret-value-12345"
KNOWN_TOKEN = "ocmort-known-resolver-token"
KNOWN_BEARER = "Bearer known-bearer-token-xyz"


def test_client_secret_not_in_exception_message(monkeypatch, respx_mock):
    """A token acquisition failure must not include the client secret."""
    import httpx

    respx_mock.post("https://idp.example.com/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_client"})
    )

    with pytest.raises(OcmoAuthError) as exc_info:
        _fetch_token(
            "https://idp.example.com/token",
            client_id="my-service",
            client_secret=KNOWN_SECRET,
            scope="openid",
            audience=None,
        )
    assert KNOWN_SECRET not in str(exc_info.value)


def test_resolver_token_not_in_logs(caplog):
    """The resolver token value must not appear in log output."""
    provider = _ResolverTokenProvider(KNOWN_TOKEN)
    headers: dict[str, str] = {}
    with caplog.at_level(logging.DEBUG, logger="ocmo"):
        provider.inject_headers(headers)

    for record in caplog.records:
        assert KNOWN_TOKEN not in record.getMessage()


def test_authorization_header_not_in_logs(caplog, monkeypatch):
    """Authorization header value must not appear in DEBUG logs."""
    # We test that the transport's _inject_auth doesn't log the header value.
    # Checking log output from the transport request call.
    from ocmo.auth import _BearerProvider

    provider = _BearerProvider("known-bearer-secret")
    headers: dict[str, str] = {}
    with caplog.at_level(logging.DEBUG, logger="ocmo"):
        provider.inject_headers(headers)

    for record in caplog.records:
        assert "known-bearer-secret" not in record.getMessage()
