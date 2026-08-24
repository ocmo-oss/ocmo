"""Resolve API smoke tests — one parametrized test per case directory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ocmo_smoke.case import SmokeCase
from ocmo_smoke.client import OcmoApiClient
from ocmo_smoke.compare import (
    ResolvedArtifact,
    assert_multiset_files_equal,
    assert_trace_equal,
    compare_item_to_file,
)


def _error_message(body: object) -> str:
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, list):
            return " ".join(str(e) for e in err)
        return str(err or body)
    return str(body)


def _fetch_resolved_artifacts(
    client: OcmoApiClient,
    namespace: str,
    case: SmokeCase,
) -> tuple[list[ResolvedArtifact], dict]:
    """Call resolve and download each item artifact."""

    resp = client.resolve(namespace, case.resolve_path, case.query)
    return resp, _parse_resolve_response(client, resp)


def _parse_resolve_response(
    client: OcmoApiClient,
    resp,
) -> list[ResolvedArtifact]:
    body = resp.body
    if not isinstance(body, dict):
        raise AssertionError(f"Expected JSON object, got: {resp.text[:500]}")

    items_raw = body.get("items") or []
    artifacts: list[ResolvedArtifact] = []
    for item in items_raw:
        url = item.get("url")
        content = b""
        if url:
            content = client.download_artifact(url)
        artifacts.append(
            ResolvedArtifact(
                name=item.get("name", ""),
                format=item.get("format", ""),
                content=content,
                trace=item.get("trace") or {},
                url=url,
                checksum=item.get("checksum"),
            )
        )
    return artifacts


@pytest.mark.smoke
def test_resolve_smoke(
    api_client: OcmoApiClient,
    smoke_case: SmokeCase,
    smoke_namespace: str,
) -> None:
    """Bootstrap case fixtures, resolve, compare to expected/ on disk."""

    expect = smoke_case.expect

    if expect.status != 200:
        resp = api_client.resolve(
            smoke_namespace,
            smoke_case.resolve_path,
            smoke_case.query,
        )
        assert resp.status_code == expect.status, (
            f"Expected HTTP {expect.status}, got {resp.status_code}\n{resp.text}"
        )
        if expect.error_substring:
            msg = _error_message(resp.body)
            assert expect.error_substring in msg, (
                f"Expected error containing {expect.error_substring!r}, got:\n{msg}"
            )
        return

    resp = api_client.resolve(
        smoke_namespace,
        smoke_case.resolve_path,
        smoke_case.query,
    )
    assert resp.ok, (
        f"Resolve failed for {smoke_case.resolve_path!r}: "
        f"HTTP {resp.status_code}\n{resp.text}"
    )

    body = resp.body
    assert isinstance(body, dict)

    if expect.trace_only:
        assert body.get("trace_only") is True, "Expected trace_only=true in response"
        trace_path = smoke_case.expected_dir / "trace.json"
        if trace_path.is_file():
            # Use first item trace or top-level — API puts trace on items
            items = body.get("items") or []
            if items:
                actual_trace = items[0].get("trace") or {}
            else:
                actual_trace = body.get("trace") or {}
            assert_trace_equal(trace_path, actual_trace)
        return

    artifacts = _parse_resolve_response(api_client, resp)

    if not expect.items:
        pytest.fail(
            f"Case {smoke_case.id}: expect.items is empty but status is 200 — "
            "add expected files under expected/"
        )

    if expect.match == "multiset":
        assert_multiset_files_equal(
            smoke_case.expected_dir,
            [spec.file for spec in expect.items],
            artifacts,
        )
        return

    if expect.sort_by_name:
        artifacts = sorted(artifacts, key=lambda a: a.name)
        expected_specs = sorted(expect.items, key=lambda e: e.name or e.file)
    else:
        expected_specs = expect.items

    if len(artifacts) != len(expected_specs):
        names = [a.name for a in artifacts]
        raise AssertionError(
            f"Item count mismatch: expected {len(expected_specs)}, got {len(artifacts)}\n"
            f"  actual names: {names}"
        )

    for spec, artifact in zip(expected_specs, artifacts, strict=True):
        if spec.name is not None:
            assert artifact.name == spec.name, (
                f"Item name mismatch: expected {spec.name!r}, got {artifact.name!r}"
            )

        expected_path = smoke_case.expected_dir / spec.file
        assert expected_path.is_file(), f"Missing expected file: {expected_path}"

        compare_item_to_file(expected_path, artifact)

    # Optional whole-response metadata checks
    meta_path = smoke_case.expected_dir / "response.json"
    if meta_path.is_file():
        expected_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if "length" in expected_meta:
            assert body.get("length") == expected_meta["length"]
