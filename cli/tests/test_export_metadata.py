"""Tests for export metadata helpers."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from ocmo_cli._export_metadata import (
    export_metadata_rows,
    metadata_file_prefix,
    write_export_xattrs,
)


def _config_item() -> SimpleNamespace:
    return SimpleNamespace(
        name="web",
        path="app/web",
        node_type="config",
        author="alice",
        description="",
        version_data=SimpleNamespace(
            version=1,
            updater="alice",
            updated_at="2026-01-01T00:00:00+00:00",
            deleted_at=None,
        ),
    )


def test_export_metadata_rows_includes_namespace() -> None:
    rows = export_metadata_rows(_config_item(), namespace="prod")
    assert rows[0] == ("namespace", "prod")
    assert ("path", "app/web") in rows
    assert ("node_type", "config") in rows


def test_metadata_file_prefix_yaml_comment_for_config() -> None:
    rows = [("path", "app/web"), ("node_type", "config")]
    prefix = metadata_file_prefix(rows, node_type="config")
    assert prefix == "# path: app/web\n# node_type: config\n"


def test_metadata_file_prefix_jinja_comment_for_template() -> None:
    rows = [("path", "app/site.conf"), ("node_type", "template")]
    prefix = metadata_file_prefix(rows, node_type="template")
    assert prefix == ("{# path: app/site.conf #}\n" "{# node_type: template #}\n")


def test_metadata_file_prefix_empty_for_secret() -> None:
    rows = [("path", "app/db"), ("node_type", "secret")]
    assert metadata_file_prefix(rows, node_type="secret") == ""


@pytest.mark.skipif(not hasattr(os, "setxattr"), reason="xattr not supported")
def test_write_export_xattrs_sets_user_ocmo_attributes(tmp_path) -> None:
    path = tmp_path / "web"
    path.write_text("body\n")
    rows = [("namespace", "prod"), ("path", "app/web"), ("version", 1)]
    write_export_xattrs(path, rows)
    try:
        assert os.getxattr(path, "user.ocmo.namespace") == b"prod"
        assert os.getxattr(path, "user.ocmo.path") == b"app/web"
        assert os.getxattr(path, "user.ocmo.version") == b"1"
    except OSError:
        pytest.skip("xattr not supported on this filesystem")
