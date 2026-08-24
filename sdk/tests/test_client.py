"""Tests for OcmoClient — configuration, namespace binding, version check."""

import httpx
import pytest

from ocmo.client import OcmoClient, _build_params, _parse_semver
from ocmo.config import OcmoConfig
from ocmo.errors import OcmoConfigError, OcmoIncompatibleVersionError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(**kwargs) -> OcmoConfig:
    return OcmoConfig(server="https://ocmo.example.com", **kwargs)


# ---------------------------------------------------------------------------
# Version parsing
# ---------------------------------------------------------------------------


def test_parse_semver_normal():
    assert _parse_semver("1.5.3") == (1, 5, 3)


def test_parse_semver_pre():
    assert _parse_semver("0.8.19") == (0, 8, 19)


def test_parse_semver_invalid():
    assert _parse_semver("not-a-version") == (0, 0, 0)


# ---------------------------------------------------------------------------
# Dynamic query param builder
# ---------------------------------------------------------------------------


def test_build_params_empty():
    assert _build_params() == {}


def test_build_params_serialises_params():
    result = _build_params(params={"env": "prod", "region": "eu"})
    assert result == {"param_env": "prod", "param_region": "eu"}


def test_build_params_serialises_cast_options():
    result = _build_params(cast_options={"indent": "2"})
    assert result == {"cast_option_indent": "2"}


def test_build_params_combined():
    result = _build_params(
        params={"env": "prod"},
        cast_options={"indent": "2"},
        extra={"version": "stable"},
    )
    assert result["param_env"] == "prod"
    assert result["cast_option_indent"] == "2"
    assert result["version"] == "stable"


def test_build_params_ignores_none_extra():
    result = _build_params(extra={"version": "latest", "cast": None})
    assert "cast" not in result
    assert result["version"] == "latest"


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------


def test_client_constructs_with_config():
    cfg = _config()
    client = OcmoClient(config=cfg)
    assert client._config.server == "https://ocmo.example.com"
    client.close()


def test_ns_requires_namespace():
    client = OcmoClient(config=_config())
    with pytest.raises(OcmoConfigError, match="namespace"):
        client.ns()
    client.close()


def test_ns_uses_default_from_config():
    client = OcmoClient(config=_config(namespace="staging"))
    view = client.ns()
    assert view._namespace == "staging"
    client.close()


def test_ns_explicit_overrides_default():
    client = OcmoClient(config=_config(namespace="staging"))
    view = client.ns("prod")
    assert view._namespace == "prod"
    client.close()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


def test_client_context_manager():
    with OcmoClient(config=_config()) as client:
        assert client._config.server == "https://ocmo.example.com"


# ---------------------------------------------------------------------------
# Version compatibility
# ---------------------------------------------------------------------------


_SERVER = "https://ocmo.example.com"


def test_incompatible_major_raises(respx_mock):
    respx_mock.get(f"{_SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "2.0.0"}))
    cfg = _config()
    client = OcmoClient(config=cfg)
    from ocmo.client import _VersionChecker

    checker = _VersionChecker("1.0.0", _SERVER)
    with pytest.raises(OcmoIncompatibleVersionError):
        checker.check(client._http)
    client.close()


def test_outside_minor_window_warns(respx_mock):
    respx_mock.get(f"{_SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "1.5.0"}))
    cfg = _config()
    client = OcmoClient(config=cfg)
    from ocmo.client import _VersionChecker

    checker = _VersionChecker("1.0.0", _SERVER)
    with pytest.warns(UserWarning, match="compatibility window"):
        checker.check(client._http)
    client.close()


def test_version_check_runs_once(respx_mock):
    """Version check must not call /api/version more than once per client."""
    respx_mock.get(f"{_SERVER}/api/version").mock(return_value=httpx.Response(200, json={"version": "0.8.19"}))
    cfg = _config()
    client = OcmoClient(config=cfg)
    from ocmo.client import _VersionChecker

    checker = _VersionChecker("0.8.19", _SERVER)
    checker.check(client._http)
    checker.check(client._http)  # second call must not hit the network
    assert respx_mock.calls.call_count == 1
    client.close()
