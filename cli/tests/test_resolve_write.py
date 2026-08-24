"""Tests for resolve filesystem output."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ocmo_cli._resolve_output import emit_write_outcome_jsonpath, emit_write_report
from ocmo_cli._resolve_write import (
    ResolveWriteOutcome,
    file_matches_checksum,
    save_resolve_item,
    write_resolve_items,
)
from ocmo_cli.commands.resolve import _save_and_report


def _item(
    *,
    name: str = "app/cfg.yaml",
    text: str = "key: value\n",
    checksum: str | None = None,
    trace: dict | None = None,
) -> SimpleNamespace:
    data = text.encode()
    if checksum is None:
        checksum = f"sha256:{hashlib.sha256(data).hexdigest()}"
    return SimpleNamespace(
        name=name,
        version=1,
        format="yaml",
        checksum=checksum,
        trace={} if trace is None else trace,
        bytes=data,
        text=text,
    )


def test_save_resolve_item_creates_missing_file(tmp_path: Path) -> None:
    dest = tmp_path / "out.yaml"
    item = _item()

    outcome = save_resolve_item(item, dest, rewrite=False, skip_existing=False)

    assert outcome.result == "created"
    assert dest.read_bytes() == item.bytes


def test_save_resolve_item_skips_unchanged_checksum(tmp_path: Path) -> None:
    dest = tmp_path / "out.yaml"
    item = _item()
    dest.write_bytes(item.bytes)

    outcome = save_resolve_item(item, dest, rewrite=False, skip_existing=False)

    assert outcome.result == "skipped"
    assert outcome.detail == "unchanged"


def test_save_resolve_item_fails_when_different_without_rewrite(tmp_path: Path) -> None:
    dest = tmp_path / "out.yaml"
    dest.write_text("other\n")
    item = _item(text="key: value\n")

    outcome = save_resolve_item(item, dest, rewrite=False, skip_existing=False)

    assert outcome.result == "failed"
    assert dest.read_text() == "other\n"


def test_save_resolve_item_rewrites_when_flag_set(tmp_path: Path) -> None:
    dest = tmp_path / "out.yaml"
    dest.write_text("other\n")
    item = _item(text="key: value\n")

    outcome = save_resolve_item(item, dest, rewrite=True, skip_existing=False)

    assert outcome.result == "rewritten"
    assert dest.read_text() == "key: value\n"


def test_save_resolve_item_skips_existing_when_flag_set(tmp_path: Path) -> None:
    dest = tmp_path / "out.yaml"
    dest.write_text("other\n")
    item = _item(text="key: value\n")

    outcome = save_resolve_item(item, dest, rewrite=False, skip_existing=True)

    assert outcome.result == "skipped"
    assert outcome.detail == "exists"
    assert dest.read_text() == "other\n"


def test_file_matches_checksum(tmp_path: Path) -> None:
    data = b"hello"
    checksum = f"sha256:{hashlib.sha256(data).hexdigest()}"
    path = tmp_path / "file"
    path.write_bytes(data)

    assert file_matches_checksum(path, checksum) is True
    assert file_matches_checksum(path, "sha256:deadbeef") is False


def test_write_resolve_items_to_dir(tmp_path: Path) -> None:
    items = [_item(name="a.yaml"), _item(name="b.yaml", text="two\n")]

    outcomes = write_resolve_items(items, output_dir=str(tmp_path))

    assert len(outcomes) == 2
    assert all(outcome.result == "created" for outcome in outcomes)
    assert (tmp_path / "a.yaml").exists()
    assert (tmp_path / "b.yaml").exists()


def test_write_resolve_items_output_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    item = _item(name="ignored/path.json", text="{}\n")

    outcomes = write_resolve_items([item], output_file="single.json")

    dest = (tmp_path / "single.json").resolve()
    assert len(outcomes) == 1
    assert outcomes[0].result == "created"
    assert outcomes[0].path == dest
    assert dest.read_text() == "{}\n"


def test_save_resolve_item_skips_checksum_when_disabled(tmp_path: Path) -> None:
    dest = tmp_path / "out.yaml"
    partial = b"value\n"
    item = _item(text="key: full\n")
    dest.write_bytes(partial)

    outcome = save_resolve_item(
        item,
        dest,
        rewrite=False,
        skip_existing=False,
        data=partial,
        skip_checksum=True,
    )

    assert outcome.result == "skipped"
    assert outcome.detail == "unchanged"


def test_save_resolve_item_property_write_ignores_artifact_checksum(tmp_path: Path) -> None:
    dest = tmp_path / "host.txt"
    item = _item(text='{"host": "db.example.com"}\n')
    dest.write_bytes(b"db.example.com\n")

    outcome = save_resolve_item(
        item,
        dest,
        rewrite=False,
        skip_existing=False,
        data=b"db.example.com\n",
        skip_checksum=True,
    )

    assert outcome.result == "skipped"
    assert dest.read_bytes() == b"db.example.com\n"


def test_save_and_report_property_writes_extracted_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ocmo.structured import path_get

    data = {"database": {"host": "db.example.com", "port": 5432}}
    raw = json.dumps(data).encode()
    item = SimpleNamespace(
        name="app.json",
        version=1,
        format="json",
        checksum=f"sha256:{hashlib.sha256(raw).hexdigest()}",
        trace={},
        bytes=raw,
    )
    item.get = lambda path: path_get(data, path)  # type: ignore[method-assign]

    monkeypatch.chdir(tmp_path)
    _save_and_report(
        [item],
        output_file="host.txt",
        output_dir=None,
        rewrite=False,
        skip_existing=False,
        output_fmt="raw",
        no_color=True,
        prop_path="database.host",
    )

    assert (tmp_path / "host.txt").read_text() == "db.example.com\n"


def test_save_and_report_property_output_dir_writes_each_item(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ocmo.structured import path_get

    def _json_item(name: str, data: dict) -> SimpleNamespace:
        raw = json.dumps(data).encode()
        item = SimpleNamespace(
            name=name,
            version=1,
            format="json",
            checksum=f"sha256:{hashlib.sha256(raw).hexdigest()}",
            trace={},
            bytes=raw,
        )
        item.get = lambda path, payload=data: path_get(payload, path)  # type: ignore[method-assign]
        return item

    items = [
        _json_item("a.json", {"value": "one"}),
        _json_item("b.json", {"value": "two"}),
    ]
    monkeypatch.chdir(tmp_path)

    _save_and_report(
        items,
        output_file=None,
        output_dir="out",
        rewrite=False,
        skip_existing=False,
        output_fmt="name",
        no_color=True,
        prop_path="value",
    )

    assert (tmp_path / "out" / "a.json").read_text() == "one\n"
    assert (tmp_path / "out" / "b.json").read_text() == "two\n"


def test_emit_write_report_json_uses_absolute_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    dest = (tmp_path / "out" / "app" / "cfg.yaml").resolve()
    outcomes = write_resolve_items([_item(name="app/cfg.yaml")], output_dir="out")
    emit_write_report(outcomes, "json", no_color=True)

    item = json.loads(capsys.readouterr().out)["items"][0]
    assert item["path"] == str(dest.resolve())
    assert Path(item["path"]).is_absolute()


def test_emit_write_report_raw_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    outcomes = [
        ResolveWriteOutcome(_item(), Path("/tmp/a.yaml"), "created"),
        ResolveWriteOutcome(_item(), Path("/tmp/b.yaml"), "skipped", "unchanged"),
    ]
    emit_write_report(outcomes, "raw", no_color=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "created /tmp/a.yaml" in captured.err
    assert "skipped /tmp/b.yaml (unchanged)" in captured.err


def test_emit_write_report_json_uses_result_not_url(capsys: pytest.CaptureFixture[str]) -> None:
    outcomes = [
        ResolveWriteOutcome(_item(name="app/cfg.yaml"), Path("/tmp/app/cfg.yaml"), "created"),
    ]
    emit_write_report(outcomes, "json", no_color=True)

    payload = json.loads(capsys.readouterr().out)
    item = payload["items"][0]
    assert item["result"] == "created"
    assert item["path"] == "/tmp/app/cfg.yaml"
    assert "url" not in item
    assert "data" not in item


def test_emit_write_report_yaml_uses_result(capsys: pytest.CaptureFixture[str]) -> None:
    outcomes = [
        ResolveWriteOutcome(_item(), Path("/tmp/out.yaml"), "rewritten"),
    ]
    emit_write_report(outcomes, "yaml", no_color=True)

    captured = capsys.readouterr().out
    assert "result: rewritten" in captured
    assert "path: /tmp/out.yaml" in captured
    assert "url:" not in captured


def test_save_and_report_raw_interleaves_metadata_and_write_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    items = [
        _item(name="a.yaml", text="one\n"),
        _item(name="b.yaml", text="two\n", trace={"dep": {}}),
    ]
    for item in items:
        dest = tmp_path / "out" / item.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(item.bytes)

    _save_and_report(
        items,
        output_file=None,
        output_dir="out",
        rewrite=False,
        skip_existing=False,
        output_fmt="raw",
        no_color=True,
    )

    err = capsys.readouterr().err
    assert err.index("# name: a.yaml") < err.index("skipped") < err.index("# name: b.yaml")
    assert "skipped" in err.split("# name: b.yaml")[0]
    assert err.split("# name: b.yaml")[1].strip().startswith("# version:")
    assert "\n\n# name: b.yaml" in err


def test_save_and_report_name_interleaves_names_and_write_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    items = [
        _item(name="a.yaml", text="one\n"),
        _item(name="b.yaml", text="two\n"),
    ]
    for item in items:
        dest = tmp_path / "out" / item.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(item.bytes)

    _save_and_report(
        items,
        output_file=None,
        output_dir="out",
        rewrite=False,
        skip_existing=False,
        output_fmt="name",
        no_color=True,
    )

    captured = capsys.readouterr()
    assert captured.out == "a.yaml\nb.yaml\n"
    err_lines = captured.err.splitlines()
    assert len(err_lines) == 2
    assert err_lines[0].startswith("skipped")
    assert err_lines[1].startswith("skipped")
    assert "a.yaml" in err_lines[0]
    assert "b.yaml" in err_lines[1]


def test_save_and_report_raw_emits_metadata_and_write_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    items = [_item(name="app/cfg.yaml")]

    _save_and_report(
        items,
        output_file="out.yaml",
        output_dir=None,
        rewrite=False,
        skip_existing=False,
        output_fmt="raw",
        no_color=True,
    )

    captured = capsys.readouterr()
    assert "# name: app/cfg.yaml" in captured.err
    assert "created" in captured.err
    assert captured.out == ""
    assert (tmp_path / "out.yaml").exists()


def test_emit_write_outcome_jsonpath_prints_detail(capsys: pytest.CaptureFixture[str]) -> None:
    outcome = ResolveWriteOutcome(_item(), Path("/tmp/out.yaml"), "skipped", "unchanged")
    emit_write_outcome_jsonpath(outcome, "items[*].detail")

    captured = capsys.readouterr()
    assert captured.out == "unchanged\n"
    assert captured.err == ""


def test_save_and_report_jsonpath_interleaves_values(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    items = [
        _item(name="a.yaml", text="one\n"),
        _item(name="b.yaml", text="two\n"),
    ]
    for item in items:
        dest = tmp_path / "out" / item.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(item.bytes)

    _save_and_report(
        items,
        output_file=None,
        output_dir="out",
        rewrite=False,
        skip_existing=False,
        output_fmt="jsonpath=items[*].detail",
        no_color=True,
    )

    captured = capsys.readouterr()
    assert captured.out == "unchanged\nunchanged\n"
    assert captured.err == ""


def test_save_and_report_name_emits_names_and_write_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    items = [_item(name="app/cfg.yaml")]

    _save_and_report(
        items,
        output_file="out.yaml",
        output_dir=None,
        rewrite=False,
        skip_existing=False,
        output_fmt="name",
        no_color=True,
    )

    captured = capsys.readouterr()
    assert captured.out == "app/cfg.yaml\n"
    assert "created" in captured.err
