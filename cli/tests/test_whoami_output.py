"""Tests for ocmo whoami output."""

from __future__ import annotations

import pytest

from ocmo_cli._output_manifest import emit_command_output, get_command_spec
from ocmo_cli._whoami_output import whoami_table_row


def test_whoami_spec_defaults_to_table_on_tty() -> None:
    spec = get_command_spec("whoami")
    assert spec.default_tty == "table"
    assert spec.default_non_tty == "yaml"
    assert "table" in spec.supported_formats


def test_whoami_table_row_flattens_user_details() -> None:
    row = whoami_table_row(
        {
            "auth_type": "user",
            "identifier": "test-admin",
            "display_name": "Test Admin",
            "access_scope": "",
            "user_details": {
                "email": "admin@example.com",
                "is_global_admin": True,
                "claims": {"email": "admin@example.com", "groups": "admins"},
            },
        }
    )
    assert row["email"] == "admin@example.com"
    assert row["is_global_admin"] is True
    assert row["claims"] == {"email": "admin@example.com", "groups": "admins"}
    assert "user_details" not in row


def test_whoami_table_row_flattens_resolver_details() -> None:
    row = whoami_table_row(
        {
            "auth_type": "resolver",
            "identifier": "app/svc",
            "display_name": "Resolver (app/svc)",
            "access_scope": "app",
            "resolver_details": {
                "namespace": "whoami-ns",
                "name": "svc",
                "token_number": 1,
            },
        }
    )
    assert row["namespace"] == "whoami-ns"
    assert row["name"] == "svc"
    assert row["token_number"] == 1
    assert "resolver_details" not in row
    assert "claims" not in row


def test_emit_command_output_whoami_table_shows_claims_column(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_command_output(
        "whoami",
        {
            "auth_type": "user",
            "identifier": "test-admin",
            "display_name": "Test Admin",
            "access_scope": "",
            "user_details": {
                "email": "admin@example.com",
                "is_global_admin": True,
                "claims": {"email": "admin@example.com", "groups": "admins"},
            },
        },
        "table",
    )
    out = capsys.readouterr().out
    assert "CLAIMS" in out
    assert "IS_GLOBAL_ADMIN" in out
    assert "USER_DETAILS" not in out
    assert "groups" in out
    assert "admins" in out
