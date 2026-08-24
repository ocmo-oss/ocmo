"""Unit tests for artifact storage and fs eviction."""

from __future__ import annotations

import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import Client, SimpleTestCase, TestCase, override_settings

from core.managers import artifacts as artifacts_mod
from core.managers.artifacts import (
    FsArtifactBackend,
    mint_token,
    sweep_fs_artifacts_if_due,
    verify_token,
)
from core.tests.namespace_helpers import create_test_namespace


class ResolveTokenTests(SimpleTestCase):
    def test_verify_token_does_not_require_request_identity(self):
        token = mint_token(
            artifact_id="a" * 64,
            namespace="ns1",
            item_path="app/cfg",
            identity="user:alice",
        )
        payload = verify_token(token)
        self.assertEqual(payload.namespace, "ns1")
        self.assertEqual(payload.item_path, "app/cfg")
        self.assertEqual(payload.identity, "user:alice")


class FsArtifactSweepTests(SimpleTestCase):
    def setUp(self):
        artifacts_mod._last_fs_sweep_at = 0.0

    def _backend(self, root: str) -> FsArtifactBackend:
        return FsArtifactBackend(root=root)

    def _write_artifact(self, backend: FsArtifactBackend, content: bytes) -> Path:
        artifact_id = backend.store(content)
        return backend._path(artifact_id)

    @override_settings(OCMO_RESOLVE_ARTIFACT_MAX_AGE=3600)
    def test_sweep_expired_removes_old_files_only(self):
        with TemporaryDirectory() as tmp:
            backend = self._backend(tmp)
            old_path = self._write_artifact(backend, b"old")
            new_path = self._write_artifact(backend, b"new")

            old_ts = time.time() - 7200
            os.utime(old_path, (old_ts, old_ts))

            removed = backend.sweep_expired()
            self.assertEqual(removed, 1)
            self.assertFalse(old_path.exists())
            self.assertTrue(new_path.exists())

    @override_settings(
        OCMO_RESOLVE_ARTIFACT_BACKEND="fs",
        OCMO_RESOLVE_ARTIFACT_SWEEP_INTERVAL=60,
        OCMO_RESOLVE_ARTIFACT_MAX_AGE=3600,
    )
    def test_sweep_if_due_runs_once_within_interval(self):
        with TemporaryDirectory() as tmp:
            with override_settings(OCMO_RESOLVE_ARTIFACT_DIR=tmp):
                backend = FsArtifactBackend()
                path = self._write_artifact(backend, b"stale")
                os.utime(path, (time.time() - 7200, time.time() - 7200))

                first = sweep_fs_artifacts_if_due()
                second = sweep_fs_artifacts_if_due()

                self.assertEqual(first, 1)
                self.assertIsNone(second)

    @override_settings(
        OCMO_RESOLVE_ARTIFACT_BACKEND="fs",
        OCMO_RESOLVE_ARTIFACT_SWEEP_INTERVAL=1,
        OCMO_RESOLVE_ARTIFACT_MAX_AGE=3600,
    )
    def test_sweep_if_due_runs_again_after_interval(self):
        with TemporaryDirectory() as tmp:
            with override_settings(OCMO_RESOLVE_ARTIFACT_DIR=tmp):
                backend = FsArtifactBackend()
                path = self._write_artifact(backend, b"stale")
                os.utime(path, (time.time() - 7200, time.time() - 7200))

                self.assertEqual(sweep_fs_artifacts_if_due(), 1)

                path = self._write_artifact(backend, b"another-stale")
                os.utime(path, (time.time() - 7200, time.time() - 7200))

                time.sleep(1.1)
                self.assertEqual(sweep_fs_artifacts_if_due(), 1)

    @override_settings(OCMO_RESOLVE_ARTIFACT_BACKEND="redis")
    def test_sweep_if_due_skips_redis_backend(self):
        self.assertIsNone(sweep_fs_artifacts_if_due())


class ResolveSweepHookTests(TestCase):
    def setUp(self):
        artifacts_mod._last_fs_sweep_at = 0.0

    @patch("core.managers.resolution.sweep_fs_artifacts_if_due")
    def test_resolve_calls_sweep_once(self, mock_sweep):
        ns = create_test_namespace("artifact-sweep-hook", description="test")
        client = Client()
        resp = client.post(
            f"/api/v1/ns/{ns.name}/~config/~create/app/cfg",
            data=b"key: value\n",
            content_type="application/yaml",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

        resp = client.get(f"/api/v1/ns/{ns.name}/~resolve/app/cfg")
        self.assertEqual(resp.status_code, 200, resp.content)
        mock_sweep.assert_called_once()
