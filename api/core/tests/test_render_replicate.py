"""Tests for render mode ``replicate``."""

from django.test import TestCase, override_settings

from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace

_TEST_MASTER_KEY = "ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs="


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class RenderReplicateTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("render-replicate")

    def test_replicate_renders_one_template_per_context(self):
        TreeManager(self.ns, "tmpl/item.yaml.j2", auth=None).create_item(
            "# ocmo.name: {{ slug }}.yaml\nvalue: {{ value }}\n",
            "template",
        )
        TreeManager(self.ns, "app/root", auth=None).create_item(
            "_ocmo:\n"
            "  render:\n"
            "    mode: replicate\n"
            "    by: .items\n"
            "    templates:\n"
            "      - tmpl/item.yaml.j2@latest\n"
            "items:\n"
            "  - {slug: alpha, value: 1}\n"
            "  - {slug: beta, value: 2}\n",
            "config",
        )
        outputs = ResolvePipelineManager(self.ns, "app/root", "latest", auth=None).resolve()
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0].name, "alpha.yaml")
        self.assertEqual(outputs[1].name, "beta.yaml")
        self.assertEqual(outputs[0].data_text, "value: 1\n")
        self.assertEqual(outputs[1].data_text, "value: 2\n")
