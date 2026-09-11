"""Integration tests for deferred ``_ocmo.name`` resolution."""

from django.test import TestCase

from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace


class OutputNameResolveContextTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("output-name-ctx")

    def _create(self, path: str, body: str) -> None:
        TreeManager(self.ns, path, auth=None).create_item(body, "config")

    def _resolve(self, path: str):
        return ResolvePipelineManager(self.ns, path, "latest", auth=None).resolve()

    def test_stack_generating_config_name_from_merged_data(self):
        self._create("bases/base", "database:\n  env: base\n")
        self._create(
            "app/prod",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: stack\n"
            "    configs:\n"
            "      - ../bases/base\n"
            "  name: app-{.database.env}.yaml\n"
            "database:\n"
            "  env: prod\n",
        )
        outputs = self._resolve("app/prod")
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].name, "app-prod.yaml")

    def test_broadcast_target_name_from_merged_overlay(self):
        self._create(
            "targets/svc-a",
            "_ocmo:\n  name: \"{._ocmo.Name}-{.region}.yaml\"\n"
            "name: svc-a\n",
        )
        self._create(
            "app/rollout",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: broadcast\n"
            "    by: .overlay\n"
            "    configs:\n"
            "      - ../targets/svc-a\n"
            "overlay:\n"
            "  region: eu\n",
        )
        outputs = self._resolve("app/rollout")
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].name, "svc-a-eu.yaml")

    def test_zip_target_name_from_merged_patch(self):
        self._create(
            "targets/base-a",
            "_ocmo:\n  name: app-{.env}.yaml\n",
        )
        self._create(
            "app/root",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: zip\n"
            "    by: .patches\n"
            "    configs:\n"
            "      - ../targets/base-a\n"
            "patches:\n"
            "  - {env: dev}\n",
        )
        outputs = self._resolve("app/root")
        self.assertEqual(outputs[0].name, "app-dev.yaml")

    def test_path_metadata_name_without_body_duplication(self):
        self._create(
            "infra/prod/clusters/eu-cluster",
            "_ocmo:\n  name: \"{._ocmo.Name}-{._ocmo.Path[-3]}.conf\"\n"
            "apiVersion: apps/v1\n",
        )
        outputs = self._resolve("infra/prod/clusters/eu-cluster")
        self.assertEqual(outputs[0].name, "eu-cluster-prod.conf")
