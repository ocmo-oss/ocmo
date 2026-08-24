"""Tests for ``ocmo diff`` address parsing and output rendering."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from ocmo_cli._address import AddressError
from ocmo_cli._diff_input import (
    DiffSpec,
    diff_sdk_kwargs,
    parse_diff_spec,
    render_diff_response,
    render_unified_diff,
)
from ocmo_cli.main import cli


def test_parse_diff_spec_version_range() -> None:
    assert parse_diff_spec(("audit-test/new.conf@2..13",)) == DiffSpec(
        path="audit-test/new.conf",
        from_ref="2",
        to_ref="13",
    )


def test_parse_diff_spec_version_range_with_flag_overrides() -> None:
    assert parse_diff_spec(
        ("app/web@2..13",),
        from_version="1",
        to_version="latest",
    ) == DiffSpec(path="app/web", from_ref="1", to_ref="latest")


def test_parse_diff_spec_single_address_version_suffix_sets_to_ref() -> None:
    assert parse_diff_spec(("app/web@5",)) == DiffSpec(
        path="app/web",
        to_ref="5",
    )


def test_parse_diff_spec_from_to_flags() -> None:
    assert parse_diff_spec(
        ("app/web",),
        from_version="3",
        to_version="5",
    ) == DiffSpec(path="app/web", from_ref="3", to_ref="5")


def test_parse_diff_spec_two_addresses_cross_path() -> None:
    assert parse_diff_spec(("app/web@2", "app/staging/web@14")) == DiffSpec(
        path="app/web",
        from_ref="2",
        to_ref="14",
        to_path="app/staging/web",
    )


def test_parse_diff_spec_two_addresses_same_path_versions() -> None:
    assert parse_diff_spec(("app/web@2", "app/web@14")) == DiffSpec(
        path="app/web",
        from_ref="2",
        to_ref="14",
    )


def test_parse_diff_spec_rejects_version_flag_with_two_addresses() -> None:
    with pytest.raises(AddressError, match="two addresses"):
        parse_diff_spec(("app/web@2", "app/other@3"), version_flag="latest")


def test_parse_diff_spec_rejects_range_with_two_addresses() -> None:
    with pytest.raises(AddressError, match="single address"):
        parse_diff_spec(("app/web@2..13", "app/other"))


def test_render_unified_diff_shows_changes() -> None:
    text = render_unified_diff(
        "alpha\nbeta\n",
        "alpha\ngamma\n",
        from_label="app/web@2",
        to_label="app/web@3",
    )
    assert "--- app/web@2" in text
    assert "+++ app/web@3" in text
    assert "-beta" in text
    assert "+gamma" in text


def test_render_unified_diff_identical() -> None:
    assert render_unified_diff("same", "same", from_label="a", to_label="b") == "No differences\n"


def test_render_diff_response_from_api_payload() -> None:
    result = SimpleNamespace(
        decryption_required=False,
        identical=False,
        from_side=SimpleNamespace(
            path="app/web",
            requested="2",
            version=2,
            data="line-one\nline-two\n",
        ),
        to_side=SimpleNamespace(
            path="app/web",
            requested="3",
            version=3,
            data="line-one\nline-three\n",
        ),
    )
    text = render_diff_response(result)
    assert "-line-two" in text
    assert "+line-three" in text


def test_render_diff_response_identical_flag() -> None:
    result = SimpleNamespace(
        decryption_required=False,
        identical=True,
        from_side=SimpleNamespace(path="app/web", requested="2", version=2, data="x"),
        to_side=SimpleNamespace(path="app/web", requested="3", version=3, data="x"),
    )
    assert render_diff_response(result) == "No differences\n"


def test_diff_help_documents_range_and_two_address_syntax() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", "--help"])
    assert result.exit_code == 0, result.output
    assert "app/web@2..13" in result.output
    assert "app/web@2 app/staging/web@14" in result.output


def test_diff_sdk_kwargs_from_version_range() -> None:
    spec = parse_diff_spec(("audit-test/new.conf@2..13",))
    path, kwargs = diff_sdk_kwargs(spec)
    assert path == "audit-test/new.conf"
    assert kwargs == {"from_": "2", "to": "13"}


def test_diff_sdk_kwargs_cross_path() -> None:
    spec = parse_diff_spec(("app/web@2", "app/staging/web@14"))
    path, kwargs = diff_sdk_kwargs(spec)
    assert path == "app/web"
    assert kwargs == {"from_": "2", "to": "14", "to_path": "app/staging/web"}


def test_render_diff_response_secret_without_reveal_returns_empty() -> None:
    result = SimpleNamespace(
        decryption_required=True,
        identical=None,
        from_side=SimpleNamespace(path="creds/db", requested="latest", version=1, data=None),
        to_side=SimpleNamespace(path="creds/db", requested="latest", version=1, data=None),
    )
    assert render_diff_response(result) == ""
