"""Tests for extend mode ``replicate``."""

import yaml
from django.test import TestCase

from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace


class ExtendReplicateTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("extend-replicate")

    def _create(self, path: str, body: str) -> None:
        TreeManager(self.ns, path, auth=None).create_item(body, "config")

    def _resolve(self, path: str):
        return ResolvePipelineManager(self.ns, path, "latest", auth=None).resolve()

    def test_replicate_merges_base_with_each_patch(self):
        self._create(
            "bases/business",
            "foo: bar\nbaz: xxx\n",
        )
        self._create(
            "app/final",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: replicate\n"
            "    by: .data\n"
            "    configs:\n"
            "      - ../bases/business\n"
            "data:\n"
            "  - baz: aaa\n"
            "    xxx: yyy\n"
            "  - baz: '555'\n"
            "    aaa: vvv\n",
        )
        outputs = self._resolve("app/final")
        self.assertEqual(len(outputs), 2)
        self.assertEqual(
            yaml.safe_load(outputs[0].data_text),
            {"foo": "bar", "baz": "aaa", "xxx": "yyy"},
        )
        self.assertEqual(
            yaml.safe_load(outputs[1].data_text),
            {"foo": "bar", "baz": "555", "aaa": "vvv"},
        )

    def test_replicate_output_names_use_numeric_suffix(self):
        self._create(
            "bases/business",
            "_ocmo:\n  name: myconf.yaml\nfoo: bar\n",
        )
        self._create(
            "app/final",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: replicate\n"
            "    by: .data\n"
            "    configs:\n"
            "      - ../bases/business\n"
            "data:\n"
            "  - {patch: a}\n"
            "  - {patch: b}\n"
            "  - {patch: c}\n",
        )
        outputs = self._resolve("app/final")
        self.assertEqual([o.name for o in outputs], ["myconf-1.yaml", "myconf-2.yaml", "myconf-3.yaml"])
