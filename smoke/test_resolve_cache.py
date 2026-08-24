"""Smoke tests for the short-circuit resolve cache.

Cache behavior is observable via the ``X-Ocmo-Resolve-Cache`` response header
(``hit`` or ``miss``) added by ``ResolveCacheHeaderMiddleware``.

Test scenarios:
- **hit**: Resolve twice with identical inputs → second is a cache hit with the
  same checksum.
- **miss on config change**: Resolve, update a config dependency, resolve again
  → cache miss; checksum changes.
- **miss on secret change**: Resolve (with secret parameter), update the secret,
  resolve again → cache miss.
- **param separation**: Two resolves with different ``param_*`` values produce
  independent cache entries (both miss on first call, both hit on repeat).
- **mark-stable bypass**: ``?mark-stable=true`` always triggers a full resolve
  (miss) regardless of cache state.

If the ``X-Ocmo-Resolve-Cache`` header is absent from responses (e.g. the API
server does not have ``ResolveCacheHeaderMiddleware`` configured) these tests
are skipped with an informative message.
"""

from __future__ import annotations

import uuid

import pytest

from ocmo_smoke.client import OcmoApiClient
from ocmo_smoke.bootstrap import bootstrap_case, grant_smoke_permissions
from ocmo_smoke.case import load_case
from pathlib import Path

CASES_ROOT = Path(__file__).parent / "cases"

_CACHE_HEADER = "X-Ocmo-Resolve-Cache"


def _require_cache_header(resp):
    """Skip test if server doesn't emit the cache header."""
    if _CACHE_HEADER not in resp.headers:
        pytest.skip(
            f"Server did not return {_CACHE_HEADER} header — "
            "ResolveCacheHeaderMiddleware may not be installed"
        )


@pytest.fixture
def cache_namespace(api_client: OcmoApiClient, keep_namespace: bool):
    """Isolated namespace with extend_accumulate case bootstrapped."""
    case = load_case(CASES_ROOT / "extend_accumulate")
    ns_name = f"smoke-cache-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    if not created.ok:
        pytest.fail(f"Could not create namespace: {created.text}")
    try:
        grant_smoke_permissions(api_client, ns_name)
        bootstrap_case(api_client, ns_name, case)
    except Exception as exc:
        if not keep_namespace:
            api_client.delete_namespace(ns_name)
        pytest.fail(f"Bootstrap failed: {exc}")
    yield ns_name
    if keep_namespace:
        print(f"\n[smoke] kept namespace: {ns_name}")
        return
    api_client.delete_namespace(ns_name)


@pytest.fixture
def secret_cache_namespace(api_client: OcmoApiClient, keep_namespace: bool):
    """Isolated namespace with secret_parameter case bootstrapped."""
    case = load_case(CASES_ROOT / "secret_parameter")
    ns_name = f"smoke-cache-sec-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    if not created.ok:
        pytest.fail(f"Could not create namespace: {created.text}")
    try:
        grant_smoke_permissions(api_client, ns_name)
        bootstrap_case(api_client, ns_name, case)
    except Exception as exc:
        if not keep_namespace:
            api_client.delete_namespace(ns_name)
        pytest.fail(f"Bootstrap failed: {exc}")
    yield ns_name
    if keep_namespace:
        print(f"\n[smoke] kept namespace: {ns_name}")
        return
    api_client.delete_namespace(ns_name)


@pytest.mark.smoke
def test_cache_hit_on_second_resolve(api_client: OcmoApiClient, cache_namespace: str):
    """Second identical resolve is a cache hit with the same checksum."""
    path = "scenario2/prod"

    r1 = api_client.resolve(cache_namespace, path)
    assert r1.ok, f"First resolve failed: {r1.text}"
    _require_cache_header(r1)

    r2 = api_client.resolve(cache_namespace, path)
    assert r2.ok, f"Second resolve failed: {r2.text}"

    assert r1.headers.get(_CACHE_HEADER) == "miss", (
        f"First resolve should be cache miss, got: {r1.headers.get(_CACHE_HEADER)!r}"
    )
    assert r2.headers.get(_CACHE_HEADER) == "hit", (
        f"Second resolve should be cache hit, got: {r2.headers.get(_CACHE_HEADER)!r}"
    )

    checksum1 = r1.body["items"][0]["checksum"]
    checksum2 = r2.body["items"][0]["checksum"]
    assert checksum1 == checksum2, (
        f"Cache hit should return same checksum: {checksum1!r} != {checksum2!r}"
    )


@pytest.mark.smoke
def test_cache_miss_after_config_update(api_client: OcmoApiClient, cache_namespace: str):
    """Cache is invalidated when a dependency config is updated."""
    path = "scenario2/prod"

    r1 = api_client.resolve(cache_namespace, path)
    assert r1.ok

    # Verify second call is a hit before we mutate anything.
    r_hit = api_client.resolve(cache_namespace, path)
    assert r_hit.ok
    _require_cache_header(r_hit)
    assert r_hit.headers.get(_CACHE_HEADER) == "hit", "Expected cache hit before update"

    # Update the base config (a dependency of prod).
    updated = api_client.update_config(
        cache_namespace,
        "scenario2/base",
        "changed: true\n",
    )
    assert updated.ok, f"Config update failed: {updated.text}"

    r2 = api_client.resolve(cache_namespace, path)
    assert r2.ok, f"Resolve after update failed: {r2.text}"

    assert r2.headers.get(_CACHE_HEADER) == "miss", (
        f"Expected cache miss after config update, got: {r2.headers.get(_CACHE_HEADER)!r}"
    )
    # Checksum must change because the content changed.
    assert r1.body["items"][0]["checksum"] != r2.body["items"][0]["checksum"], (
        "Checksum should change after config update"
    )


@pytest.mark.smoke
def test_cache_miss_after_secret_update(
    api_client: OcmoApiClient, secret_cache_namespace: str
):
    """Cache is invalidated when a secret referenced by a parameter is updated."""
    path = "scenario7/use-secret"

    r1 = api_client.resolve(secret_cache_namespace, path)
    assert r1.ok, f"First resolve failed: {r1.text}"
    _require_cache_header(r1)

    r_hit = api_client.resolve(secret_cache_namespace, path)
    assert r_hit.ok
    assert r_hit.headers.get(_CACHE_HEADER) == "hit", "Expected hit before secret update"

    # Update the secret.
    updated = api_client.update_secret(
        secret_cache_namespace,
        "scenario7/creds/db",
        "password: new-rotated-password\n",
    )
    assert updated.ok, f"Secret update failed: {updated.text}"

    r2 = api_client.resolve(secret_cache_namespace, path)
    assert r2.ok, f"Resolve after secret update failed: {r2.text}"

    assert r2.headers.get(_CACHE_HEADER) == "miss", (
        f"Expected miss after secret update, got: {r2.headers.get(_CACHE_HEADER)!r}"
    )


@pytest.mark.smoke
def test_cache_param_separation(api_client: OcmoApiClient, keep_namespace: bool):
    """Different ?param_* values produce independent cache entries."""
    case = load_case(CASES_ROOT / "parameters_override")
    ns_name = f"smoke-cache-params-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    if not created.ok:
        pytest.fail(f"Could not create namespace: {created.text}")
    try:
        grant_smoke_permissions(api_client, ns_name)
        bootstrap_case(api_client, ns_name, case)
    except Exception as exc:
        if not keep_namespace:
            api_client.delete_namespace(ns_name)
        pytest.fail(f"Bootstrap failed: {exc}")

    try:
        path = "infra/prod/clusters/eu-cluster"

        r1a = api_client.resolve(ns_name, path, {"param_replicas": "2"})
        assert r1a.ok
        _require_cache_header(r1a)

        r1b = api_client.resolve(ns_name, path, {"param_replicas": "5"})
        assert r1b.ok

        # Both first calls should be misses.
        assert r1a.headers.get(_CACHE_HEADER) == "miss"
        assert r1b.headers.get(_CACHE_HEADER) == "miss"

        # Second calls with same params should be hits.
        r2a = api_client.resolve(ns_name, path, {"param_replicas": "2"})
        r2b = api_client.resolve(ns_name, path, {"param_replicas": "5"})
        assert r2a.headers.get(_CACHE_HEADER) == "hit", "param=2 second call should hit"
        assert r2b.headers.get(_CACHE_HEADER) == "hit", "param=5 second call should hit"

        # The two entries should have different checksums (different content).
        assert r1a.body["items"][0]["checksum"] != r1b.body["items"][0]["checksum"], (
            "Different param values should produce different checksums"
        )
    finally:
        if not keep_namespace:
            api_client.delete_namespace(ns_name)


@pytest.mark.smoke
def test_l1_cast_hit_on_different_cast_format(
    api_client: OcmoApiClient, cache_namespace: str
):
    """Layer 1 hit: resolving with a different cast format skips the pipeline.

    1st call (default/yaml cast)  → miss  (populates L1).
    2nd call (json cast)          → cast  (L1 hit, re-cast performed).
    3rd call (same json cast)     → hit   (L2 hit, no cast performed).
    """
    path = "scenario2/prod"

    r1 = api_client.resolve(cache_namespace, path)
    assert r1.ok, f"1st resolve failed: {r1.text}"
    _require_cache_header(r1)
    assert r1.headers.get(_CACHE_HEADER) == "miss", (
        f"1st resolve should be miss, got: {r1.headers.get(_CACHE_HEADER)!r}"
    )

    r2 = api_client.resolve(cache_namespace, path, {"cast": "json"})
    assert r2.ok, f"2nd resolve (json) failed: {r2.text}"
    assert r2.headers.get(_CACHE_HEADER) == "cast", (
        f"2nd resolve with different cast should be 'cast', "
        f"got: {r2.headers.get(_CACHE_HEADER)!r}"
    )

    # Checksums differ — different serialisation format.
    checksum1 = r1.body["items"][0]["checksum"]
    checksum2 = r2.body["items"][0]["checksum"]
    assert checksum1 != checksum2, (
        "YAML and JSON representations should have different checksums"
    )

    # Third call with same cast → pure L2 hit.
    r3 = api_client.resolve(cache_namespace, path, {"cast": "json"})
    assert r3.ok, f"3rd resolve (json) failed: {r3.text}"
    assert r3.headers.get(_CACHE_HEADER) == "hit", (
        f"3rd resolve should be 'hit', got: {r3.headers.get(_CACHE_HEADER)!r}"
    )
    assert r2.body["items"][0]["checksum"] == r3.body["items"][0]["checksum"], (
        "L2 hit should return the same checksum as the L1 hit that preceded it"
    )


@pytest.mark.smoke
def test_mark_stable_bypasses_cache(api_client: OcmoApiClient, cache_namespace: str):
    """?mark-stable=true always triggers a full resolve (cache miss)."""
    path = "scenario2/prod"

    # Warm the cache.
    r1 = api_client.resolve(cache_namespace, path)
    assert r1.ok
    r_hit = api_client.resolve(cache_namespace, path)
    _require_cache_header(r_hit)
    assert r_hit.headers.get(_CACHE_HEADER) == "hit", "Expected hit before mark-stable call"

    # mark-stable=true should force a full resolve.
    r_stable = api_client.resolve(cache_namespace, path, {"mark-stable": "true"})
    assert r_stable.ok, f"mark-stable resolve failed: {r_stable.text}"
    assert r_stable.headers.get(_CACHE_HEADER) == "miss", (
        f"mark-stable should bypass cache, got: {r_stable.headers.get(_CACHE_HEADER)!r}"
    )

    # Verify stable tag was advanced.
    item = api_client.get_item(cache_namespace, path)
    assert item.ok
    version = r_stable.body["items"][0]["version"]
    tags = item.body.get("tags", {})
    assert tags.get("stable") == version, (
        f"stable tag should be {version}, got: {tags.get('stable')!r}"
    )


_RESTRICTED_RESOLVE_PERMISSIONS = """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "*"
    actions:
      - config:resolve
    resources:
      - scenario2/prod
"""


@pytest.mark.smoke
def test_cache_hit_denies_when_extend_dependency_permission_revoked(
    api_client: OcmoApiClient, cache_namespace: str
):
    """Cache hit re-checks config:resolve on extend participants, not only the root."""
    path = "scenario2/prod"
    grant_smoke_permissions(api_client, cache_namespace)

    r1 = api_client.resolve(cache_namespace, path)
    assert r1.ok, f"First resolve failed: {r1.text}"
    _require_cache_header(r1)

    r_hit = api_client.resolve(cache_namespace, path)
    assert r_hit.ok
    assert r_hit.headers.get(_CACHE_HEADER) == "hit", "Expected cache hit before permission change"

    updated = api_client.update_config(
        cache_namespace,
        "_permissions",
        _RESTRICTED_RESOLVE_PERMISSIONS,
    )
    assert updated.ok, f"Permission update failed: {updated.text}"

    r_denied = api_client.resolve(cache_namespace, path)
    assert r_denied.status_code == 403, (
        f"Expected 403 after revoking nested resolve permission, "
        f"got {r_denied.status_code}: {r_denied.text[:200]}"
    )


@pytest.mark.smoke
def test_l1_cache_hit_denies_when_extend_dependency_permission_revoked(
    api_client: OcmoApiClient, cache_namespace: str
):
    """L1 cast hit also re-checks permissions on extend participants."""
    path = "scenario2/prod"
    grant_smoke_permissions(api_client, cache_namespace)

    r1 = api_client.resolve(cache_namespace, path)
    assert r1.ok, f"1st resolve failed: {r1.text}"
    _require_cache_header(r1)
    assert r1.headers.get(_CACHE_HEADER) == "miss"

    r2 = api_client.resolve(cache_namespace, path, {"cast": "json"})
    assert r2.ok, f"2nd resolve (json) failed: {r2.text}"
    assert r2.headers.get(_CACHE_HEADER) == "cast"

    updated = api_client.update_config(
        cache_namespace,
        "_permissions",
        _RESTRICTED_RESOLVE_PERMISSIONS,
    )
    assert updated.ok, f"Permission update failed: {updated.text}"

    r3 = api_client.resolve(cache_namespace, path, {"cast": "json"})
    assert r3.status_code == 403, (
        f"Expected 403 on L1 hit after permission change, "
        f"got {r3.status_code}: {r3.text[:200]}"
    )


@pytest.mark.smoke
def test_no_creds_cache_survives_secret_update(
    api_client: OcmoApiClient, secret_cache_namespace: str
):
    """no-creds cache is not invalidated when a referenced secret is updated."""
    path = "scenario7/use-secret"
    query = {"no-creds": "true"}

    r1 = api_client.resolve(secret_cache_namespace, path, query)
    assert r1.ok, f"First resolve failed: {r1.text}"
    _require_cache_header(r1)
    checksum1 = r1.body["items"][0]["checksum"]

    updated = api_client.update_secret(
        secret_cache_namespace,
        "scenario7/creds/db",
        "password: rotated-secret\n",
    )
    assert updated.ok, f"Secret update failed: {updated.text}"

    r2 = api_client.resolve(secret_cache_namespace, path, query)
    assert r2.ok, f"Second resolve failed: {r2.text}"
    assert r2.headers.get(_CACHE_HEADER) == "hit", (
        f"no-creds resolve should stay cached after secret update, "
        f"got: {r2.headers.get(_CACHE_HEADER)!r}"
    )
    assert r2.body["items"][0]["checksum"] == checksum1


@pytest.mark.smoke
def test_no_creds_and_full_resolve_cache_independent(
    api_client: OcmoApiClient, secret_cache_namespace: str
):
    """Full and no-creds resolves use separate cache entries."""
    path = "scenario7/use-secret"

    r_full = api_client.resolve(secret_cache_namespace, path)
    assert r_full.ok, f"Full resolve failed: {r_full.text}"
    _require_cache_header(r_full)
    checksum_full = r_full.body["items"][0]["checksum"]

    r_nocreds = api_client.resolve(
        secret_cache_namespace, path, {"no-creds": "true"}
    )
    assert r_nocreds.ok, f"no-creds resolve failed: {r_nocreds.text}"
    assert r_nocreds.headers.get(_CACHE_HEADER) == "miss", (
        "no-creds resolve should miss when only full resolve is cached"
    )
    checksum_nocreds = r_nocreds.body["items"][0]["checksum"]
    assert checksum_full != checksum_nocreds
