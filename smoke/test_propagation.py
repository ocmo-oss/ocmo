"""Propagation API smoke tests — one parametrized test per case directory."""

from __future__ import annotations

from pathlib import Path

import pytest

from ocmo_smoke.bootstrap import _bootstrap_configs, grant_smoke_permissions
from ocmo_smoke.client import OcmoApiClient
from ocmo_smoke.propagation_case import (
    PropagationCase,
    discover_propagation_cases,
    iter_propagation_configs,
)

CASES_ROOT = Path(__file__).parent / "cases"


def _error_message(body: object) -> str:
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, list):
            return " ".join(str(e) for e in err)
        return str(err or body)
    return str(body)


def _config_data(api_client: OcmoApiClient, namespace: str, path: str) -> str:
    got = api_client.get_item(namespace, path)
    assert got.status_code == 200, got.text
    assert isinstance(got.body, dict)
    version_data = got.body.get("version_data")
    assert isinstance(version_data, dict), got.body
    data = version_data.get("data")
    assert isinstance(data, str), version_data
    return data


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "propagation_case" in metafunc.fixturenames:
        cases = discover_propagation_cases(CASES_ROOT)
        metafunc.parametrize(
            "propagation_case",
            cases,
            ids=[c.id for c in cases],
        )


@pytest.fixture
def propagation_namespace(
    api_client: OcmoApiClient,
    propagation_case: PropagationCase,
    keep_namespace: bool,
) -> str:
    import uuid

    ns_name = f"smoke-{propagation_case.id}-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    assert created.status_code in (200, 201), created.text
    try:
        grant_smoke_permissions(api_client, ns_name)
        _bootstrap_configs(api_client, ns_name, iter_propagation_configs(propagation_case))
        for path, rel_file in propagation_case.updates:
            contents = (propagation_case.root / rel_file).read_text(encoding="utf-8")
            updated = api_client.update_config(ns_name, path, contents)
            assert updated.status_code == 200, updated.text
    except Exception as exc:
        if not keep_namespace:
            api_client.delete_namespace(ns_name)
        pytest.fail(f"Bootstrap failed for case {propagation_case.id}: {exc}")
    yield ns_name
    if keep_namespace:
        print(f"\n[smoke] kept namespace for debugging: {ns_name}")
        return
    deleted = api_client.delete_namespace(ns_name)
    if deleted.status_code not in (200, 204, 404):
        print(
            f"\n[smoke] warning: failed to delete namespace {ns_name}: "
            f"HTTP {deleted.status_code} {deleted.text}"
        )


@pytest.mark.smoke
def test_propagation_smoke(
    api_client: OcmoApiClient,
    propagation_case: PropagationCase,
    propagation_namespace: str,
) -> None:
    """Bootstrap case fixtures, run propagation action, assert expectations."""

    expect = propagation_case.expect
    ns = propagation_namespace

    if propagation_case.action == "propagate":
        resp = api_client.propagate_config(
            ns,
            propagation_case.source_path,
            version=propagation_case.propagate_version,
        )
    elif propagation_case.action == "tag":
        assert propagation_case.tag_name is not None
        assert propagation_case.tag_version is not None
        resp = api_client.set_tag(
            ns,
            propagation_case.source_path,
            propagation_case.tag_name,
            version=propagation_case.tag_version,
        )
    elif propagation_case.action == "resolve":
        path = propagation_case.resolve_path or propagation_case.source_path
        resp = api_client.resolve(ns, path, propagation_case.resolve_query)
    else:
        pytest.fail(f"Unknown propagation action {propagation_case.action!r}")

    if expect.status != 200:
        assert resp.status_code == expect.status, resp.text
        if expect.error_substring:
            assert expect.error_substring in _error_message(resp.body)
        return

    assert resp.status_code == 200, resp.text
    body = resp.body
    assert isinstance(body, dict)

    if propagation_case.action == "tag" and expect.propagation is not None:
        if expect.propagation:
            assert body.get("propagation") is not None
        else:
            assert body.get("propagation") is None

    if propagation_case.action == "propagate":
        targets = body.get("targets") or []
    elif propagation_case.action == "tag" and body.get("propagation"):
        targets = body["propagation"].get("targets") or []
    else:
        targets = []

    for expected_target in expect.targets:
        matched = next(
            (t for t in targets if t.get("path") == expected_target.path),
            None,
        )
        if expected_target.status is not None:
            if matched is None and expected_target.file:
                pass  # resolve/stable triggers have no propagation payload
            else:
                assert matched is not None, (
                    f"Target {expected_target.path!r} not in response: {targets}"
                )
                assert matched.get("status") == expected_target.status

        if expected_target.file:
            target_path = expected_target.path.split("@", 1)[0]
            actual = _config_data(api_client, ns, target_path)
            expected = (
                propagation_case.expected_dir / expected_target.file
            ).read_text(encoding="utf-8")
            assert actual == expected, (
                f"Config {target_path!r} content mismatch for case {propagation_case.id}"
            )
