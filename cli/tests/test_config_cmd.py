"""Tests for ocmo config command."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from ocmo_cli._config import load_config
from ocmo_cli.main import cli


def test_config_help_shows_config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    monkeypatch.setenv("OCMO_CONFIG", str(cfg))
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "Config file:" in result.output
    assert cfg.name in result.output.replace("\n", "")
    assert "(not created yet)" in result.output


def test_set_context_creates_auth_stub(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "config",
            "set-context",
            "dev",
            "--server",
            "http://localhost:8080",
            "--auth",
            "dev",
            "--namespace",
            "my-ns",
        ],
    )
    assert result.exit_code == 0, result.output

    cfg = load_config()
    assert "dev" in cfg.contexts
    assert cfg.contexts["dev"].auth == "dev"
    assert "dev" in cfg.auths
    assert cfg.auths["dev"].mode == "oidc"
    assert cfg.auths["dev"].issuer == ""
    assert cfg.auths["dev"].client_id == ""


def test_set_auth_updates_auth_block(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("auths:\n" "  dev:\n" "    mode: oidc\n")
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "config",
            "set-auth",
            "dev",
            "--issuer",
            "http://localhost:8080/dex",
            "--client-id",
            "ocmo-cli",
        ],
    )
    assert result.exit_code == 0, result.output

    raw = yaml.safe_load(cfg_path.read_text())
    assert raw["auths"]["dev"] == {
        "mode": "oidc",
        "issuer": "http://localhost:8080/dex",
        "client_id": "ocmo-cli",
    }


def test_set_auth_creates_missing_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["config", "set-auth", "issuer", "--client-id", "ocmo-cli"],
    )
    assert result.exit_code == 0, result.output

    cfg = load_config()
    assert cfg.auths["issuer"].mode == "oidc"
    assert cfg.auths["issuer"].client_id == "ocmo-cli"


def test_current_ns_from_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("current-context: dev\n" "contexts:\n" "  dev:\n" "    namespace: my-first-namespace\n")
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.delenv("OCMO_NAMESPACE", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "current-ns"])
    assert result.exit_code == 0
    assert result.output.strip() == "my-first-namespace"


def test_current_ns_env_overrides_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("current-context: dev\n" "contexts:\n" "  dev:\n" "    namespace: from-context\n")
    cfg_path.chmod(0o600)
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.setenv("OCMO_NAMESPACE", "from-env")

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "current-ns"])
    assert result.exit_code == 0
    assert result.output.strip() == "from-env"


def test_current_ns_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "config.yaml"
    monkeypatch.setenv("OCMO_CONFIG", str(cfg_path))
    monkeypatch.delenv("OCMO_NAMESPACE", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "current-ns"])
    assert result.exit_code == 0
    assert result.output.strip() == "(none)"
