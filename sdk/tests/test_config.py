"""Tests for OcmoConfig and environment variable resolution."""

import pytest

from ocmo.config import _CLIENT_VARS, _SERVER_SIDE_VARS, OcmoConfig
from ocmo.errors import OcmoConfigError


def _make(server: str = "https://ocmo.example.com", **kwargs) -> OcmoConfig:
    return OcmoConfig(server=server, **kwargs)


# ---------------------------------------------------------------------------
# Server URL validation
# ---------------------------------------------------------------------------


def test_valid_server_url():
    cfg = _make()
    assert cfg.base_url == "https://ocmo.example.com/api/v1"


def test_server_with_path_rejected():
    with pytest.raises(OcmoConfigError, match="no path"):
        _make(server="https://ocmo.example.com/api")


def test_server_missing_rejected():
    with pytest.raises(OcmoConfigError):
        OcmoConfig(server="")


def test_server_bad_scheme_rejected():
    with pytest.raises(OcmoConfigError, match="http"):
        _make(server="ftp://ocmo.example.com")


# ---------------------------------------------------------------------------
# Env var precedence
# ---------------------------------------------------------------------------


def test_env_takes_lower_precedence_than_arg(monkeypatch):
    monkeypatch.setenv("OCMO_SERVER", "https://env.example.com")
    cfg = OcmoConfig.from_env(server="https://arg.example.com")
    assert cfg.server == "https://arg.example.com"


def test_env_used_when_no_arg(monkeypatch):
    monkeypatch.setenv("OCMO_SERVER", "https://env.example.com")
    cfg = OcmoConfig.from_env()
    assert cfg.server == "https://env.example.com"


def test_int_env_var(monkeypatch):
    monkeypatch.setenv("OCMO_RETRIES", "5")
    monkeypatch.setenv("OCMO_SERVER", "https://x.example.com")
    cfg = OcmoConfig.from_env()
    assert cfg.retries == 5


def test_invalid_int_env_var_raises(monkeypatch):
    monkeypatch.setenv("OCMO_RETRIES", "not-a-number")
    monkeypatch.setenv("OCMO_SERVER", "https://x.example.com")
    with pytest.raises(OcmoConfigError, match="integer"):
        OcmoConfig.from_env()


# ---------------------------------------------------------------------------
# Auth mode inference
# ---------------------------------------------------------------------------


def test_infer_resolver_token(monkeypatch):
    monkeypatch.setenv("OCMO_SERVER", "https://x.example.com")
    monkeypatch.setenv("OCMO_TOKEN", "ocmort-abc123")
    cfg = OcmoConfig.from_env()
    assert cfg.auth_mode == "resolver-token"


def test_infer_bearer(monkeypatch):
    monkeypatch.setenv("OCMO_SERVER", "https://x.example.com")
    monkeypatch.setenv("OCMO_TOKEN", "eyJhbGciOi...")
    cfg = OcmoConfig.from_env()
    assert cfg.auth_mode == "bearer"


def test_infer_oidc_from_client_id(monkeypatch):
    monkeypatch.setenv("OCMO_SERVER", "https://x.example.com")
    monkeypatch.setenv("OCMO_CLIENT_ID", "my-service")
    monkeypatch.setenv("OCMO_CLIENT_SECRET", "secret")
    cfg = OcmoConfig.from_env()
    assert cfg.auth_mode == "oidc"


def test_ambiguous_auth_raises(monkeypatch):
    monkeypatch.setenv("OCMO_SERVER", "https://x.example.com")
    monkeypatch.setenv("OCMO_TOKEN", "ocmort-abc")
    monkeypatch.setenv("OCMO_CLIENT_ID", "my-service")
    with pytest.raises(OcmoConfigError, match="[Aa]mbiguous"):
        OcmoConfig.from_env()


# ---------------------------------------------------------------------------
# Variable namespace disjointness (§7 — must not reuse server-side names)
# ---------------------------------------------------------------------------


def test_client_server_var_sets_disjoint():
    overlap = _CLIENT_VARS & _SERVER_SIDE_VARS
    assert not overlap, f"SDK client variables overlap with server-side names: {overlap}"


# ---------------------------------------------------------------------------
# TLS warning
# ---------------------------------------------------------------------------


def test_insecure_tls_emits_warning():
    with pytest.warns(UserWarning, match="TLS verification is disabled"):
        OcmoConfig(server="https://x.example.com", insecure_skip_tls_verify=True)


# ---------------------------------------------------------------------------
# Secret file
# ---------------------------------------------------------------------------


def test_secret_file_read(tmp_path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("my-secret\n")
    cfg = OcmoConfig.from_env(
        server="https://x.example.com",
        client_id="svc",
        client_secret_file=str(secret_file),
    )
    assert cfg.client_secret == "my-secret"


def test_both_secret_and_file_raises(tmp_path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("x")
    with pytest.raises(OcmoConfigError, match="not both"):
        OcmoConfig.from_env(
            server="https://x.example.com",
            client_secret="direct",
            client_secret_file=str(secret_file),
        )


def test_invalid_oidc_grant_type_raises(monkeypatch):
    monkeypatch.setenv("OCMO_SERVER", "https://x.example.com")
    monkeypatch.setenv("OCMO_OIDC_GRANT_TYPE", "implicit")
    with pytest.raises(OcmoConfigError, match="OCMO_OIDC_GRANT_TYPE"):
        OcmoConfig.from_env()


def test_password_grant_config_from_env(monkeypatch):
    monkeypatch.setenv("OCMO_SERVER", "https://x.example.com")
    monkeypatch.setenv("OCMO_CLIENT_ID", "ocmo-sdk")
    monkeypatch.setenv("OCMO_OIDC_GRANT_TYPE", "password")
    monkeypatch.setenv("OCMO_OIDC_USERNAME", "admin@example.com")
    monkeypatch.setenv("OCMO_OIDC_PASSWORD", "password")
    cfg = OcmoConfig.from_env()
    assert cfg.oidc_grant_type == "password"
    assert cfg.oidc_username == "admin@example.com"
    assert cfg.oidc_password == "password"
