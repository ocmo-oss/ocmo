"""Unit tests for the two-layer resolve cache.

Covers:
- L1 hit when only the cast format differs (no pipeline run).
- L1 hit writes L2 so the next identical-cast request is a pure L2 hit.
- Secret-bearing resolutions skip L1 (different cast forces a full pipeline run).
- _cache_status returns correct tier string.
"""

from unittest.mock import patch

from django.core.cache import caches
from django.test import Client, TestCase, override_settings

from core.managers.resolution import ResolutionManager
from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace
from core.utils.permissions_compiler import PermissionsCompiler

_TEST_MASTER_KEY = "ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs="

_CACHE_HEADER = "X-Ocmo-Resolve-Cache"


class TwoLayerCacheApiTests(TestCase):
    """Integration-style tests exercising the cache via the HTTP API."""

    def setUp(self):
        caches["resolve"].clear()
        self.client = Client()
        self.ns = create_test_namespace("twolayer-test", description="test")
        self._create_config("app/cfg", "key: value\nnum: 1\n")

    def _create_config(self, path: str, body: str):
        r = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/{path}",
            data=body.encode(),
            content_type="application/yaml",
        )
        self.assertEqual(r.status_code, 201, r.content)

    def _resolve(self, path: str, **params):
        from urllib.parse import urlencode

        qs = urlencode(params)
        url = f"/api/v1/ns/{self.ns.name}/~resolve/{path}"
        if qs:
            url += f"?{qs}"
        return self.client.get(url)

    def _cache_header(self, response) -> str | None:
        return response.get(_CACHE_HEADER)

    # ------------------------------------------------------------------

    def test_second_resolve_same_cast_is_l2_hit(self):
        """Baseline: two identical resolves → second is a full L2 hit."""
        r1 = self._resolve("app/cfg", cast="json")
        self.assertEqual(r1.status_code, 200, r1.content)

        r2 = self._resolve("app/cfg", cast="json")
        self.assertEqual(r2.status_code, 200, r2.content)

        self.assertEqual(self._cache_header(r1), "miss")
        self.assertEqual(self._cache_header(r2), "hit")

    def test_different_cast_uses_l1_no_pipeline(self):
        """After warm with cast=yaml, requesting cast=json skips the pipeline (L1 hit)."""
        # Warm cache with default (yaml) cast.
        r1 = self._resolve("app/cfg")
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(self._cache_header(r1), "miss")

        # Request a different cast format — should hit L1, not run the pipeline.
        with patch(
            "core.managers.resolution.ResolvePipelineManager.resolve",
            wraps=None,
        ) as mock_pipeline:
            mock_pipeline.side_effect = AssertionError("Pipeline should not have been called on an L1 hit")
            r2 = self._resolve("app/cfg", cast="json")

        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(self._cache_header(r2), "cast")

    def test_l1_hit_writes_l2_so_third_call_is_hit(self):
        """L1 hit populates L2; the next identical request is a pure L2 hit."""
        # 1st call: full pipeline, warms L1.
        r1 = self._resolve("app/cfg")
        self.assertEqual(self._cache_header(r1), "miss")

        # 2nd call: different cast → L1 hit, writes L2.
        r2 = self._resolve("app/cfg", cast="json")
        self.assertEqual(self._cache_header(r2), "cast")

        # 3rd call: same cast as 2nd → L2 hit.
        r3 = self._resolve("app/cfg", cast="json")
        self.assertEqual(self._cache_header(r3), "hit")

    def test_different_cast_produces_different_content(self):
        """Resolving the same config with different casts yields different content."""
        r_yaml = self._resolve("app/cfg", cast="yaml")
        self.assertEqual(r_yaml.status_code, 200)

        r_json = self._resolve("app/cfg", cast="json")
        self.assertEqual(r_json.status_code, 200)

        checksum_yaml = r_yaml.json()["items"][0]["checksum"]
        checksum_json = r_json.json()["items"][0]["checksum"]
        self.assertNotEqual(checksum_yaml, checksum_json)


_EXTEND_YAML = """\
_ocmo:
  extend:
    mode: accumulate
    configs:
      - ../shared/base@latest
key: child
"""


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class CacheHitParticipantPermissionTests(TestCase):
    """L1/L2 cache hits re-check permissions on all participants."""

    def setUp(self):
        caches["resolve"].clear()
        PermissionsCompiler._policy_cache.clear()
        self.client = Client()
        self.ns = create_test_namespace("cache-participant-perm", description="test")
        TreeManager(self.ns, "shared/base", auth=None).create_item("base: true\n", "config")
        TreeManager(self.ns, "app/cfg", auth=None).create_item(_EXTEND_YAML, "config")

    def _resolve(self, path: str, **params):
        from urllib.parse import urlencode

        qs = urlencode(params)
        url = f"/api/v1/ns/{self.ns.name}/~resolve/{path}"
        if qs:
            url += f"?{qs}"
        return self.client.get(url)

    def test_l1_cast_hit_denies_when_nested_permission_revoked(self):
        """L1 hit still enforces config:resolve on extend participants."""
        r1 = self._resolve("app/cfg")
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(r1.get(_CACHE_HEADER), "miss")

        r2 = self._resolve("app/cfg", cast="json")
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(r2.get(_CACHE_HEADER), "cast")

        TreeManager(self.ns, "_permissions", auth=None).update_item(
            """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "*"
    actions:
      - config:resolve
    resources:
      - app/**
"""
        )
        PermissionsCompiler._policy_cache.clear()

        r3 = self._resolve("app/cfg", cast="json")
        self.assertEqual(r3.status_code, 403, r3.content)


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class SecretBearingCacheTests(TestCase):
    """Secret-bearing resolutions must not be stored at Layer 1."""

    def setUp(self):
        caches["resolve"].clear()
        self.client = Client()
        self.ns = create_test_namespace("secret-cache-test", description="test")
        # Create a secret with a version.
        r = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~secret/~create/creds/db",
            data=b"password: hunter2\n",
            content_type="application/yaml",
        )
        self.assertEqual(r.status_code, 201, r.content)
        # Config references the secret via a parameter.
        cfg_body = (
            "_ocmo:\n"
            "  parameters:\n"
            "    db_password:\n"
            "      type: secret\n"
            "      value: creds/db@latest\n"
            "      description: Database password\n"
            "db_pass: '{!db_password}'\n"
        )
        r2 = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/secret-cfg",
            data=cfg_body.encode(),
            content_type="application/yaml",
        )
        self.assertEqual(r2.status_code, 201, r2.content)

    def _resolve(self, cast: str | None = None):
        url = f"/api/v1/ns/{self.ns.name}/~resolve/app/secret-cfg"
        if cast:
            url += f"?cast={cast}"
        return self.client.get(url)

    def test_secret_config_different_cast_reruns_pipeline(self):
        """Secret-bearing config: changing cast must run the full pipeline (no L1)."""
        r1 = self._resolve()
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(r1.get(_CACHE_HEADER), "miss")

        # Different cast should be a miss, not 'cast', because L1 was skipped.
        r2 = self._resolve(cast="json")
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(r2.get(_CACHE_HEADER), "miss")


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class NoCredsCacheTests(TestCase):
    """no-creds resolutions skip secret participants and may use Layer 1."""

    def setUp(self):
        caches["resolve"].clear()
        self.client = Client()
        self.ns = create_test_namespace("nocreds-cache-test", description="test")
        r = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~secret/~create/creds/db",
            data=b"password: hunter2\n",
            content_type="application/yaml",
        )
        self.assertEqual(r.status_code, 201, r.content)
        cfg_body = (
            "_ocmo:\n"
            "  parameters:\n"
            "    db_password:\n"
            "      type: secret\n"
            "      value: creds/db@latest\n"
            "      description: Database password\n"
            "db_pass: '{!db_password}'\n"
        )
        r2 = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/secret-cfg",
            data=cfg_body.encode(),
            content_type="application/yaml",
        )
        self.assertEqual(r2.status_code, 201, r2.content)

    def _resolve(self, **params):
        from urllib.parse import urlencode

        qs = urlencode(params)
        url = f"/api/v1/ns/{self.ns.name}/~resolve/app/secret-cfg"
        if qs:
            url += f"?{qs}"
        return self.client.get(url)

    def test_no_creds_secret_config_uses_l1_cache(self):
        """no-creds: changing cast hits L1 (cast header), unlike full secret resolve."""
        r1 = self._resolve(**{"no-creds": "true"})
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(r1.get(_CACHE_HEADER), "miss")

        r2 = self._resolve(**{"no-creds": "true", "cast": "json"})
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(r2.get(_CACHE_HEADER), "cast")

    def test_no_creds_cache_key_separate_from_full_resolve(self):
        r_full = self._resolve()
        self.assertEqual(r_full.status_code, 200, r_full.content)
        checksum_full = r_full.json()["items"][0]["checksum"]

        r_nocreds = self._resolve(**{"no-creds": "true"})
        self.assertEqual(r_nocreds.status_code, 200, r_nocreds.content)
        checksum_nocreds = r_nocreds.json()["items"][0]["checksum"]
        self.assertNotEqual(checksum_full, checksum_nocreds)

        r_nocreds2 = self._resolve(**{"no-creds": "true"})
        self.assertEqual(r_nocreds2.get(_CACHE_HEADER), "hit")
        self.assertEqual(
            r_nocreds2.json()["items"][0]["checksum"],
            checksum_nocreds,
        )


from django.test import SimpleTestCase


class CacheKeyUnitTests(SimpleTestCase):
    def test_no_creds_changes_resolution_key(self):
        from core.managers.resolve_cache import ResolveCacheManager

        k_false = ResolveCacheManager.make_resolution_key("ns", "path", "latest", {}, no_creds=False)
        k_true = ResolveCacheManager.make_resolution_key("ns", "path", "latest", {}, no_creds=True)
        self.assertNotEqual(k_false, k_true)

    def test_no_creds_changes_artifact_key(self):
        from core.managers.resolve_cache import ResolveCacheManager

        k_false = ResolveCacheManager.make_artifact_key("ns", "path", "latest", "yaml", {}, {}, no_creds=False)
        k_true = ResolveCacheManager.make_artifact_key("ns", "path", "latest", "yaml", {}, {}, no_creds=True)
        self.assertNotEqual(k_false, k_true)


class CacheStatusUnitTests(SimpleTestCase):
    """Unit tests for ResolutionManager._cache_status (no DB required)."""

    def _status(self, cache_values: list[str]) -> str:
        items = [{"_cache": v} for v in cache_values]
        return ResolutionManager._cache_status(items)

    def test_empty_is_miss(self):
        self.assertEqual(ResolutionManager._cache_status([]), "miss")

    def test_all_hit(self):
        self.assertEqual(self._status(["hit", "hit"]), "hit")

    def test_all_cast(self):
        self.assertEqual(self._status(["cast", "cast"]), "cast")

    def test_all_miss(self):
        self.assertEqual(self._status(["miss"]), "miss")

    def test_mixed_hit_and_cast_is_cast(self):
        # All served from cache (no pipeline), but some re-cast → 'cast'.
        self.assertEqual(self._status(["hit", "cast"]), "cast")

    def test_any_miss_dominates(self):
        self.assertEqual(self._status(["hit", "miss"]), "miss")
        self.assertEqual(self._status(["cast", "miss"]), "miss")
