"""Integration tests for global resolved output name deduplication."""

from django.test import TestCase

from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace


class OutputNameDedupTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("output-name-dedup")

    def test_zip_duplicate_targets_get_deduplicated_names(self):
        TreeManager(self.ns, "bases/shared", auth=None).create_item(
            "_ocmo:\n  name: conf.yaml\nkey: base\n",
            "config",
        )
        TreeManager(self.ns, "app/root", auth=None).create_item(
            "_ocmo:\n"
            "  extend:\n"
            "    mode: zip\n"
            "    by: .patches\n"
            "    configs:\n"
            "      - ../bases/shared\n"
            "      - ../bases/shared\n"
            "      - ../bases/shared\n"
            "patches:\n"
            "  - {tier: a}\n"
            "  - {tier: b}\n"
            "  - {tier: c}\n",
            "config",
        )
        outputs = ResolvePipelineManager(self.ns, "app/root", "latest", auth=None).resolve()
        self.assertEqual(len(outputs), 3)
        self.assertEqual([o.name for o in outputs], ["conf.yaml", "conf-1.yaml", "conf-2.yaml"])
