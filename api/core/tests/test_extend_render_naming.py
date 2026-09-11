"""Extend + render output naming."""

from django.test import TestCase

from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace


class ExtendRenderNamingTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("extend-render-naming")

    def test_render_header_overrides_extend_resolved_name(self):
        TreeManager(self.ns, "bases/base", auth=None).create_item(
            "database:\n  env: base\n",
            "config",
        )
        TreeManager(self.ns, "tmpl/out.j2", auth=None).create_item(
            "# ocmo.name: {{ app_name }}.conf\nvalue: {{ app_name }}\n",
            "template",
        )
        TreeManager(self.ns, "app/root", auth=None).create_item(
            "_ocmo:\n"
            "  extend:\n"
            "    mode: stack\n"
            "    configs:\n"
            "      - ../bases/base\n"
            "  name: ignored.yaml\n"
            "  render:\n"
            "    templates:\n"
            "      - tmpl/out.j2@latest\n"
            "app_name: stacked\n",
            "config",
        )
        outputs = ResolvePipelineManager(self.ns, "app/root", "latest", auth=None).resolve()
        self.assertEqual(outputs[0].name, "stacked.conf")

    def test_render_without_header_uses_extend_resolved_name(self):
        TreeManager(self.ns, "bases/base", auth=None).create_item(
            "database:\n  env: base\n",
            "config",
        )
        TreeManager(self.ns, "tmpl/out.j2", auth=None).create_item(
            "rendered: {{ message }}\n",
            "template",
        )
        TreeManager(self.ns, "app/root", auth=None).create_item(
            "_ocmo:\n"
            "  extend:\n"
            "    mode: stack\n"
            "    configs:\n"
            "      - ../bases/base\n"
            "  name: stack-{.database.env}.yaml\n"
            "  render:\n"
            "    templates:\n"
            "      - tmpl/out.j2@latest\n"
            "database:\n"
            "  env: prod\n"
            "message: hello\n",
            "config",
        )
        outputs = ResolvePipelineManager(self.ns, "app/root", "latest", auth=None).resolve()
        self.assertEqual(outputs[0].name, "stack-prod.yaml")
        self.assertEqual(outputs[0].data_text, "rendered: hello\n")

    def test_render_without_header_uses_template_leaf_when_no_ocmo_name(self):
        TreeManager(self.ns, "tmpl/out.j2", auth=None).create_item(
            "value: {{ value }}\n",
            "template",
        )
        TreeManager(self.ns, "app/root", auth=None).create_item(
            "_ocmo:\n  render:\n    templates:\n      - tmpl/out.j2@latest\nvalue: demo\n",
            "config",
        )
        outputs = ResolvePipelineManager(self.ns, "app/root", "latest", auth=None).resolve()
        self.assertEqual(outputs[0].name, "out.j2")
