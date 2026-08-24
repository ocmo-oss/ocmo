"""Tests for resolve command output formatting."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ocmo_cli._resolve_output import (
    emit_resolve_raw,
    emit_resolve_results,
    resolve_output_format,
)


def _item(
    *,
    name: str = "app/cfg.yaml",
    version: int = 1,
    fmt: str = "yaml",
    checksum: str = "sha256:abc",
    text: str = "key: value\n",
    data: object | None = None,
    trace: dict | None = None,
) -> SimpleNamespace:
    payload = {"key": "value"} if data is None and fmt == "yaml" else data
    return SimpleNamespace(
        name=name,
        version=version,
        format=fmt,
        checksum=checksum,
        trace={} if trace is None else trace,
        url="https://example.com/download",
        text=text,
        data=payload if payload is not None else text,
    )


def test_resolve_output_format_defaults_to_raw() -> None:
    assert resolve_output_format(None, "table") == "raw"
    assert resolve_output_format(None, None) == "raw"


def test_resolve_output_format_accepts_jsonpath() -> None:
    assert resolve_output_format("jsonpath=$.items[*].name", None) == "jsonpath=$.items[*].name"


def test_emit_resolve_raw_writes_metadata_to_stderr_and_content_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    items = [
        _item(
            name="blabla.conf",
            text="some: content\n",
            trace={"steps": [{"path": "app/cfg", "version": 1}]},
        ),
        _item(name="path/my.template", fmt="raw", text="Some content\n"),
    ]
    emit_resolve_raw(items, no_color=True)

    captured = capsys.readouterr()
    assert "# name: blabla.conf" in captured.err
    assert "# checksum: sha256:abc" in captured.err
    assert "# format: yaml" in captured.err
    assert "# trace:" in captured.err
    assert "#   steps:" in captured.err
    assert "#   - path: app/cfg" in captured.err
    assert "some: content" in captured.out
    assert "Some content" in captured.out
    assert captured.out.index("some: content") < captured.out.index("Some content")
    assert "\n\n" in captured.out


def test_emit_resolve_raw_trace_nested_dependencies_indented(
    capsys: pytest.CaptureFixture[str],
) -> None:
    items = [
        _item(
            trace={
                "first/config@5": {
                    "nested/config@2": {
                        "deepest/config@4": {},
                    },
                },
            },
        ),
    ]
    emit_resolve_raw(items, no_color=True)
    err = capsys.readouterr().err
    assert ("# trace:\n" "#   first/config@5:\n" "#     nested/config@2:\n" "#       deepest/config@4: {}\n") in err


def test_emit_resolve_raw_trace_dict_keys_indented(capsys: pytest.CaptureFixture[str]) -> None:
    items = [
        _item(
            trace={
                "audit-test/temp.late@2": {},
                "secret:audit-test/secret.string@3": {},
            },
        ),
    ]
    emit_resolve_raw(items, no_color=True)
    err = capsys.readouterr().err
    assert "# trace:\n#   audit-test/temp.late@2: {}\n#   secret:audit-test/secret.string@3: {}\n" in err


def test_emit_resolve_json_replaces_url_with_data(capsys: pytest.CaptureFixture[str]) -> None:
    items = [_item()]
    emit_resolve_results(items, "json", no_color=True)

    payload = json.loads(capsys.readouterr().out)
    assert payload["length"] == 1
    item = payload["items"][0]
    assert "url" not in item
    assert item["data"] == "key: value\n"
    assert isinstance(item["data"], str)
    assert item["name"] == "app/cfg.yaml"


def test_emit_resolve_json_data_is_raw_string_for_json_artifacts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    items = [
        _item(
            fmt="json",
            text='{"hello": "world"}\n',
            data={"hello": "world"},
        ),
    ]
    emit_resolve_results(items, "json", no_color=True)
    item = json.loads(capsys.readouterr().out)["items"][0]
    assert item["data"] == '{"hello": "world"}\n'
    assert isinstance(item["data"], str)


def test_emit_resolve_name_lists_paths(capsys: pytest.CaptureFixture[str]) -> None:
    items = [_item(name="a.conf"), _item(name="b/c.conf")]
    emit_resolve_results(items, "name", no_color=True)
    assert capsys.readouterr().out == "a.conf\nb/c.conf\n"


def test_emit_resolve_jsonpath(capsys: pytest.CaptureFixture[str]) -> None:
    items = [_item(name="a.conf"), _item(name="b.conf")]
    emit_resolve_results(items, "jsonpath=items[*].name", no_color=True)
    assert capsys.readouterr().out.strip() == "a.conf\nb.conf"


def test_trace_only_payload_keeps_url(capsys: pytest.CaptureFixture[str]) -> None:
    items = [_item()]
    emit_resolve_results(items, "json", no_color=True, include_data=False)
    item = json.loads(capsys.readouterr().out)["items"][0]
    assert "url" in item
    assert "data" not in item
