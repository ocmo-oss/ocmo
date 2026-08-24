"""Tests for global permission CLI output."""

from __future__ import annotations

import pytest

from ocmo_cli._globalpermission_output import (
    format_section_claims,
    global_permission_table_row,
)
from ocmo_cli._output_manifest import emit_command_output


def test_global_permission_table_row_flattens_namespace_and_rule_id() -> None:
    row = global_permission_table_row(
        {
            "id": "ead38b7a-515d-4bd3-afb4-99715746c858",
            "position": 1.0,
            "rule": {
                "id": "dev-read",
                "namespace": "dev-*",
                "read": {"actors": []},
            },
        }
    )
    assert row["id"] == "dev-read"
    assert row["namespace"] == "dev-*"
    assert row["position"] == 1.0


def test_emit_command_output_get_globalpermission_table_shows_namespace(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_command_output(
        "get globalpermission",
        {
            "rules": [
                {
                    "id": "ead38b7a-515d-4bd3-afb4-99715746c858",
                    "position": 2.0,
                    "rule": {"id": "team-write", "namespace": "team-*"},
                },
            ],
            "count": 1,
        },
        "table",
    )
    out = capsys.readouterr().out
    assert "team-*" in out
    assert "team-write" in out


def test_format_section_claims_joins_actor_claims_with_and() -> None:
    section = {
        "actors": [
            {"kind": "User", "claims": {"groups": "team-devs", "email": "admin@example.com"}},
        ],
    }
    assert format_section_claims(section) == "email=admin@example.com AND groups=team-devs"


def test_format_section_claims_joins_actors_with_or() -> None:
    section = {
        "actors": [
            {"kind": "User", "claims": {"email": "admin@example.com"}},
            {"kind": "User", "claims": {"groups": "team-devs"}},
        ],
    }
    assert format_section_claims(section) == "email=admin@example.com OR groups=team-devs"


def test_format_section_claims_parenthesizes_and_blocks_in_or_expression() -> None:
    section = {
        "actors": [
            {"kind": "User", "claims": {"groups": "devs", "email": "admin@example.com"}},
            {"kind": "User", "claims": {"email": "bob@example.com"}},
        ],
    }
    assert format_section_claims(section) == ("(email=admin@example.com AND groups=devs) OR email=bob@example.com")


def test_global_permission_wide_row_expands_permission_sections() -> None:
    row = global_permission_table_row(
        {
            "id": "ead38b7a-515d-4bd3-afb4-99715746c858",
            "position": 1.0,
            "rule": {
                "id": "dev-read",
                "namespace": "dev-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                "write": {"actors": [{"kind": "User", "claims": {"email": "bob@example.com"}}]},
            },
        },
        wide=True,
    )
    assert row["read"] == "email=*"
    assert row["write"] == "email=bob@example.com"
    assert row["delete"] == ""
    assert row["audit"] == ""
    assert "rule" not in row


def test_emit_command_output_get_globalpermission_wide_shows_claim_columns(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emit_command_output(
        "get globalpermission",
        {
            "rules": [
                {
                    "id": "ead38b7a-515d-4bd3-afb4-99715746c858",
                    "position": 1.0,
                    "rule": {
                        "id": "dev-read",
                        "namespace": "dev-*",
                        "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                        "audit": {"actors": [{"kind": "User", "claims": {"groups": "auditors"}}]},
                    },
                },
            ],
            "count": 1,
        },
        "wide",
    )
    out = capsys.readouterr().out
    assert "READ" in out
    assert "email=*" in out
    assert "groups=auditors" in out
    assert "rule" not in out.lower()
