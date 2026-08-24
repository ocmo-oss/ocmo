"""Tests for operational health and version endpoints."""

from unittest.mock import patch

from django.core.cache import caches
from django.test import Client, TestCase, override_settings

from core.managers.health import HealthManager


class VersionEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_version_returns_product_and_version(self):
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["product"], "ocmo")
        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+")
        self.assertEqual(data["license"], "Apache-2.0")
        self.assertEqual(data["license_name"], "Apache License, Version 2.0")
        self.assertNotIn("notice", data)
        self.assertEqual(data["config_metadata_key"], "_ocmo")
        self.assertIn("builtin_namespace_paths", data)
        self.assertEqual(
            data["builtin_namespace_paths"]["config"],
            ["_git_sync", "_permissions", "_webhooks"],
        )
        self.assertEqual(
            data["builtin_namespace_paths"]["secret"],
            ["_git_sync_secret", "_webhooks_secret"],
        )
        self.assertIn("_permissions.schema", data["builtin_namespace_paths"]["schema"])
        self.assertIn("_permissions", data["builtin_namespace_paths"]["order"])
        self.assertEqual(data["reserved_tags"]["config"], ["latest", "stable"])
        self.assertEqual(data["reserved_tags"]["template"], ["latest"])
        self.assertEqual(data["reserved_tags"]["secret"], ["latest"])
        self.assertIn("auth", data)
        self.assertIn("oidc", data["auth"])

    @override_settings(
        OIDC_ISSUER="http://localhost:8080/dex",
        OIDC_CLIENT_ID="ocmo-api",
        OIDC_AUTHORIZATION_URL="http://localhost:8080/dex/auth",
        OIDC_TOKEN_URL="http://localhost:8080/dex/token",
        OIDC_SCOPES="openid profile email groups",
    )
    def test_version_returns_oidc_auth(self):
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)
        oidc = response.json()["auth"]["oidc"]
        self.assertEqual(oidc["issuer"], "http://localhost:8080/dex")
        self.assertEqual(oidc["client_id"], "ocmo-api")
        self.assertEqual(oidc["authorization_url"], "http://localhost:8080/dex/auth")
        self.assertEqual(oidc["token_url"], "http://localhost:8080/dex/token")
        self.assertEqual(oidc["scopes"], "openid profile email groups")

    @override_settings(OCMO_CONFIG_METADATA_KEY="meta")
    def test_version_returns_config_metadata_key_from_settings(self):
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["config_metadata_key"], "meta")

    def test_version_does_not_require_auth(self):
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)

    def test_version_includes_notice_when_requested(self):
        response = self.client.get("/api/version", {"notice": "true"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("notice", data)
        self.assertIn("STATEMENT ON RUSSIAN WAR CRIMES IN UKRAINE", data["notice"])
        self.assertIn("OCMO", data["notice"])


class HealthEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_ok_when_database_available(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["checks"]["database"]["status"], "ok")
        self.assertNotIn("resolve_cache_redis", data["checks"])
        self.assertNotIn("resolve_artifact_redis", data["checks"])

    def test_health_does_not_require_auth(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

    def test_health_reports_database_failure(self):
        with patch("core.managers.health.connection.ensure_connection", side_effect=RuntimeError("db down")):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["checks"]["database"]["status"], "error")
        self.assertIn("db down", data["checks"]["database"]["message"])

    @override_settings(OCMO_RESOLVE_CACHE_BACKEND="redis")
    def test_health_checks_resolve_cache_redis_when_configured(self):
        caches["resolve"].clear()
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"]["resolve_cache_redis"]["status"], "ok")

    @override_settings(OCMO_RESOLVE_CACHE_BACKEND="redis")
    def test_health_reports_resolve_cache_redis_failure(self):
        with patch.object(
            HealthManager,
            "_check_resolve_cache_redis",
            return_value={"status": "error", "message": "redis down"},
        ):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["checks"]["resolve_cache_redis"]["status"], "error")
        self.assertIn("redis down", data["checks"]["resolve_cache_redis"]["message"])

    @override_settings(OCMO_RESOLVE_ARTIFACT_BACKEND="redis")
    def test_health_checks_resolve_artifact_redis_when_configured(self):
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.return_value.ping.return_value = True
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"]["resolve_artifact_redis"]["status"], "ok")

    @override_settings(OCMO_RESOLVE_ARTIFACT_BACKEND="redis")
    def test_health_reports_resolve_artifact_redis_failure(self):
        with patch("redis.from_url") as mock_from_url:
            mock_from_url.return_value.ping.side_effect = RuntimeError("artifact redis down")
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["checks"]["resolve_artifact_redis"]["status"], "error")
        self.assertIn("artifact redis down", data["checks"]["resolve_artifact_redis"]["message"])
