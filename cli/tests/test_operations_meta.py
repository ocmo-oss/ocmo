"""Tests for bundled operation metadata."""

from __future__ import annotations

from ocmo_cli._operations_meta import load_operations_meta


def test_load_operations_meta_includes_client_scoped_namespace_ops(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "ocmo_cli._operations_meta._try_load_monorepo_yaml",
        lambda: None,
    )
    load_operations_meta.cache_clear()

    meta = load_operations_meta()
    assert meta["list_namespaces"]["scope"] == "client"
    assert meta["show_namespace"]["scope"] == "client"
    assert meta["get_item"]["scope"] == "namespace"
