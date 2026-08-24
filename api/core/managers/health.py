"""Operational health checks for core application dependencies."""

from __future__ import annotations

from django.conf import settings
from django.core.cache import caches
from django.db import connection


class HealthManager:
    """Validate that required runtime dependencies are reachable."""

    def check(self) -> dict:
        checks = {
            "database": self._check_database(),
        }
        if settings.OCMO_RESOLVE_CACHE_BACKEND == "redis":
            checks["resolve_cache_redis"] = self._check_resolve_cache_redis()
        if settings.OCMO_RESOLVE_ARTIFACT_BACKEND == "redis":
            checks["resolve_artifact_redis"] = self._check_resolve_artifact_redis()

        status = "ok" if all(item["status"] == "ok" for item in checks.values()) else "error"
        return {"status": status, "checks": checks}

    def _check_database(self) -> dict:
        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {"status": "ok"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def _check_resolve_cache_redis(self) -> dict:
        try:
            cache = caches["resolve"]
            probe_key = "ocmo:health:ping"
            cache.set(probe_key, "1", timeout=10)
            if cache.get(probe_key) != "1":
                raise RuntimeError("resolve cache read/write mismatch")
            return {"status": "ok"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def _check_resolve_artifact_redis(self) -> dict:
        try:
            import redis

            client = redis.from_url(
                settings.OCMO_RESOLVE_ARTIFACT_REDIS_URL,
                decode_responses=False,
            )
            client.ping()
            return {"status": "ok"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
