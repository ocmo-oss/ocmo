"""Tests for auth command helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from ocmo_cli._config import load_config
from ocmo_cli.commands.auth import (
    _build_auth_status,
    _describe_token_expiry,
    resolve_login_auth,
)
from ocmo_cli.main import cli


def test_auth_help_shows_config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    monkeypatch.setenv("OCMO_CONFIG", str(cfg))
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "--help"])
    assert result.exit_code == 0
    assert cfg.name in result.output.replace("\n", "")


def test_auth_status_json_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "current-context: dev\n"
        "contexts:\n"
        "  dev:\n"
        "    server: https://cfg.example.com\n"
        "    namespace: cfg-ns\n"
    )
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.setenv("OCMO_SERVER", "https://env.example.com")
    monkeypatch.delenv("OCMO_NAMESPACE", raising=False)
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)

    ctx = MagicMock(skip_version_check=True)
    ctx.client.side_effect = RuntimeError("no network")

    report = _build_auth_status(ctx)
    assert report["server"]["value"] == "https://env.example.com"
    assert report["server"]["source"] == "environment"
    assert report["namespace"]["value"] == "cfg-ns"
    assert report["namespace"]["source"] == "config"
    assert report["config_file"]["path"] == str(cfg_path)


def test_resolve_login_auth_from_env_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "current-context: default\n"
        "contexts:\n"
        "  default:\n"
        "    server: http://localhost:8080\n"
        "    auth: issuer\n"
    )
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.setenv("OCMO_OIDC_ISSUER", "http://localhost:8080/dex")
    monkeypatch.setenv("OCMO_CLIENT_ID", "ocmo-sdk")
    monkeypatch.setenv("OCMO_CLIENT_SECRET", "secret")

    from ocmo_cli._client import build_ocmo_config

    cfg = load_config()
    sdk_cfg = build_ocmo_config()
    auth = resolve_login_auth(cfg, cfg.contexts["default"], sdk_cfg)
    assert auth.issuer == "http://localhost:8080/dex"
    assert auth.client_id == "ocmo-sdk"
    assert auth.client_secret == "secret"


def test_resolve_login_auth_requires_auths_or_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "current-context: default\n"
        "contexts:\n"
        "  default:\n"
        "    server: http://localhost:8080\n"
        "    auth: issuer\n"
    )
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.delenv("OCMO_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)
    monkeypatch.delenv("OCMO_CLIENT_SECRET", raising=False)
    monkeypatch.setattr("ocmo_cli._client._fetch_oidc_from_server", lambda _server: {})
    monkeypatch.setattr("ocmo_cli.commands.auth._fetch_oidc_from_server", lambda _server: {})

    from ocmo_cli._client import build_ocmo_config

    cfg = load_config()
    sdk_cfg = build_ocmo_config(skip_version_check=True, validate_auth=False)
    with pytest.raises(ValueError, match="OIDC issuer and client_id"):
        resolve_login_auth(cfg, cfg.contexts["default"], sdk_cfg)


def test_resolve_login_auth_bootstraps_from_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "current-context: dev\n"
        "contexts:\n"
        "  dev:\n"
        "    server: http://localhost:8080\n"
        "    auth: dev\n"
        "auths:\n"
        "  dev:\n"
        "    mode: oidc\n"
    )
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.delenv("OCMO_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)
    monkeypatch.setattr(
        "ocmo_cli._client._fetch_oidc_from_server",
        lambda _server: {
            "issuer": "http://localhost:8080/dex",
            "client_id": "ocmo-cli",
        },
    )

    from ocmo_cli._client import build_ocmo_config

    cfg = load_config()
    sdk_cfg = build_ocmo_config(skip_version_check=True, validate_auth=False)
    auth = resolve_login_auth(cfg, cfg.contexts["dev"], sdk_cfg)
    assert auth.issuer == "http://localhost:8080/dex"
    assert auth.client_id == "ocmo-cli"


def test_build_ocmo_config_requires_auths_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "current-context: dev\n"
        "auths: {}\n"
        "contexts:\n"
        "  dev:\n"
        "    server: http://localhost:8080\n"
        "    auth: dev\n"
    )
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)
    monkeypatch.delenv("OCMO_OIDC_ISSUER", raising=False)

    from ocmo.errors import OcmoConfigError

    from ocmo_cli._client import build_ocmo_config

    with pytest.raises(OcmoConfigError, match="auths.dev is missing"):
        build_ocmo_config(skip_version_check=True)


def test_build_ocmo_config_bootstraps_oidc_from_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "current-context: dev\n"
        "contexts:\n"
        "  dev:\n"
        "    server: http://localhost:8080\n"
        "    auth: dev\n"
        "auths:\n"
        "  dev:\n"
        "    mode: oidc\n"
    )
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)
    monkeypatch.delenv("OCMO_OIDC_ISSUER", raising=False)
    monkeypatch.setattr(
        "ocmo_cli._client._fetch_oidc_from_server",
        lambda _server: {
            "issuer": "http://localhost:8080/dex",
            "client_id": "ocmo-api",
        },
    )

    from ocmo_cli._client import build_ocmo_config

    sdk_cfg = build_ocmo_config(skip_version_check=True)
    assert sdk_cfg.client_id == "ocmo-api"
    assert sdk_cfg.oidc_issuer == "http://localhost:8080/dex"


def test_build_ocmo_config_uses_auth_profile_for_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "current-context: dev\n"
        "contexts:\n"
        "  dev:\n"
        "    server: http://localhost:8080\n"
        "    auth: dev\n"
        "auths:\n"
        "  dev:\n"
        "    mode: oidc\n"
        "    issuer: http://localhost:8080/dex\n"
        "    client_id: ocmo-cli\n"
    )
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)
    monkeypatch.delenv("OCMO_OIDC_ISSUER", raising=False)

    from ocmo_cli._client import build_ocmo_config

    sdk_cfg = build_ocmo_config(skip_version_check=True)
    assert sdk_cfg.oidc_cache_profile == "dev"
    assert sdk_cfg.client_id == "ocmo-cli"


def test_oidc_cache_separate_per_auth_profile(tmp_path: Path) -> None:
    from ocmo.auth import oidc_cache_status, store_oidc_access_token
    from ocmo.config import OcmoConfig

    base = dict(
        server="http://localhost:8080",
        client_id="ocmo-cli",
        oidc_issuer="http://localhost:8080/dex",
        cache_dir=tmp_path,
        skip_version_check=True,
    )
    alice = OcmoConfig.from_env(**base, oidc_cache_profile="alice")
    bob = OcmoConfig.from_env(**base, oidc_cache_profile="bob")
    store_oidc_access_token(alice, "token-alice", 3600)
    store_oidc_access_token(bob, "token-bob", 3600)
    assert oidc_cache_status(alice)["cached"] is True
    assert oidc_cache_status(bob)["cached"] is True
    from ocmo.auth import oidc_token_cache

    assert oidc_token_cache(alice)._key != oidc_token_cache(bob)._key


def test_pkce_redirect_uri_and_callback_port() -> None:
    from ocmo_cli.commands.auth import (
        CLI_CALLBACK_PORT,
        _ensure_callback_port_available,
        _pkce_redirect_uri,
    )

    assert _pkce_redirect_uri() == f"http://127.0.0.1:{CLI_CALLBACK_PORT}/callback"
    assert _ensure_callback_port_available() == CLI_CALLBACK_PORT


def test_wait_for_authorization_code_accepts_callback() -> None:
    import threading
    import urllib.request

    from ocmo_cli.commands.auth import (
        CLI_CALLBACK_PORT,
        _ensure_callback_port_available,
        _pkce_redirect_uri,
        _wait_for_authorization_code,
    )

    port = CLI_CALLBACK_PORT
    _ensure_callback_port_available(port)
    state = "test-state"

    def _hit_callback() -> None:
        import time

        time.sleep(0.2)
        url = _pkce_redirect_uri(port) + f"?code=abc123&state={state}"
        urllib.request.urlopen(url, timeout=5)

    threading.Thread(target=_hit_callback, daemon=True).start()
    assert _wait_for_authorization_code(port, state, timeout=5.0) == "abc123"


def test_build_ocmo_config_rejects_missing_oidc_without_auths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("current-context: default\n" "contexts:\n" "  default:\n" "    server: http://localhost:8080\n")
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)
    monkeypatch.delenv("OCMO_OIDC_ISSUER", raising=False)

    from ocmo.errors import OcmoConfigError

    from ocmo_cli._client import build_ocmo_config

    with pytest.raises(OcmoConfigError, match="no auth: field"):
        build_ocmo_config(skip_version_check=True)


def test_build_ocmo_config_resolver_token_skips_oidc_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "current-context: default\n"
        "contexts:\n"
        "  default:\n"
        "    server: http://localhost:8080\n"
        "    namespace: my-ns\n"
    )
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.setenv("OCMO_TOKEN", "ocmort-testtoken123456789012345")
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)
    monkeypatch.delenv("OCMO_OIDC_ISSUER", raising=False)

    monkeypatch.setattr(
        "ocmo_cli._client._fetch_oidc_from_server",
        lambda _server: {
            "issuer": "http://localhost:8080/dex",
            "client_id": "ocmo-api",
        },
    )

    from ocmo_cli._client import build_ocmo_config

    sdk_cfg = build_ocmo_config(skip_version_check=True)
    assert sdk_cfg.auth_mode == "resolver-token"
    assert sdk_cfg.token == "ocmort-testtoken123456789012345"
    assert sdk_cfg.client_id is None


def test_describe_token_expiry_valid_and_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed = 1_700_000_000.0
    monkeypatch.setattr("ocmo_cli.commands.auth.time.time", lambda: fixed)

    valid = _describe_token_expiry(fixed + 3600)
    assert valid["status"] == "valid"
    assert valid["valid"] is True
    assert valid["expires_in"] == "in 1 hour"
    assert valid["expires_in_seconds"] == 3600
    assert valid["expires_at"] is not None

    expired = _describe_token_expiry(fixed - 120)
    assert expired["status"] == "expired"
    assert expired["valid"] is False
    assert expired["expires_in"] == "expired 2 minutes ago"


def test_oidc_cache_info_includes_expiry_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    from ocmo_cli.commands.auth import _oidc_cache_info

    fixed = 1_700_000_000.0
    monkeypatch.setattr("ocmo_cli.commands.auth.time.time", lambda: fixed)

    class _Cfg:
        auth_mode = "oidc"
        client_id = "ocmo-api"

    monkeypatch.setattr(
        "ocmo.auth.oidc_cache_status",
        lambda _cfg: {"cached": True, "expires_at": fixed + 1800},
    )
    info = _oidc_cache_info(_Cfg())
    assert info is not None
    assert info["cached"] is True
    assert info["status"] == "valid"
    assert info["expires_in"] == "in 30 minutes"
    assert info["expires_in_seconds"] == 1800


def test_auth_status_json_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("current-context: dev\ncontexts:\n  dev:\n    server: https://x.example.com\n")
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.setenv("OCMO_SKIP_VERSION_CHECK", "1")
    monkeypatch.delenv("OCMO_NAMESPACE", raising=False)
    monkeypatch.delenv("OCMO_CLIENT_ID", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "status", "-o", "json"])
    assert result.exit_code == 0
    # Warnings may precede JSON when config permissions are checked on stderr only;
    # stdout should be pure JSON.
    data = json.loads(result.output.strip())
    assert data["config_file"]["path"] == str(cfg_path)
    assert "server" in data
