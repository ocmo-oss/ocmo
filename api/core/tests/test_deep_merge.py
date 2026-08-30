"""Tests for extend deep-merge and list-index directive semantics."""

from django.test import TestCase

from core.constants.resolve import OMIT
from core.utils.deep_merge import apply_list_directives, deep_merge


class DeepMergeListDirectiveTests(TestCase):
    def test_int_key_dict_merges_mapping_at_index(self):
        base = [
            {
                "args": ["--v=2"],
                "image": "quay.io/app:v1",
                "name": "app",
            }
        ]
        directives = {0: {"image": "dummy:1.0.0"}}
        result = apply_list_directives(base, directives)
        self.assertEqual(
            result[0],
            {
                "args": ["--v=2"],
                "image": "dummy:1.0.0",
                "name": "app",
            },
        )

    def test_int_key_dict_replaces_non_mapping_element(self):
        base = ["item1", "item2"]
        directives = {0: {"only": "dict"}}
        result = apply_list_directives(base, directives)
        self.assertEqual(result, [{"only": "dict"}, "item2"])

    def test_int_key_dict_replaces_scalar_element(self):
        base = ["item1", "item2"]
        directives = {0: "replaced"}
        result = apply_list_directives(base, directives)
        self.assertEqual(result, ["replaced", "item2"])

    def test_int_key_dict_appends_and_prepends(self):
        base = [{"one": "two"}, {"three": "four"}]
        directives = {
            99: {"five": "appended"},
            -1: {"zero": "prepended"},
        }
        result = apply_list_directives(base, directives)
        self.assertEqual(
            result,
            [
                {"zero": "prepended"},
                {"one": "two"},
                {"three": "four"},
                {"five": "appended"},
            ],
        )

    def test_int_key_dict_merge_updates_mapping_field(self):
        base = [{"one": "two"}, {"three": "four"}]
        directives = {0: {"one": "changed value"}}
        result = apply_list_directives(base, directives)
        self.assertEqual(
            result,
            [
                {"one": "changed value"},
                {"three": "four"},
            ],
        )

    def test_deep_merge_list_with_int_key_dict(self):
        base = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "args": ["--v=2"],
                                "image": "quay.io/app:v1",
                                "name": "app",
                            }
                        ]
                    }
                }
            }
        }
        updater = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": {
                            0: {"image": "dummy:1.0.0"},
                        }
                    }
                }
            }
        }
        merged = deep_merge(base, updater)
        container = merged["spec"]["template"]["spec"]["containers"][0]
        self.assertEqual(container["image"], "dummy:1.0.0")
        self.assertEqual(container["args"], ["--v=2"])
        self.assertEqual(container["name"], "app")

    def test_deep_merge_list_concatenation_without_int_keys(self):
        base = {"tags": ["foo", "bar"]}
        updater = {"tags": ["baz"]}
        merged = deep_merge(base, updater)
        self.assertEqual(merged["tags"], ["foo", "bar", "baz"])

    def test_omit_at_list_index_removes_item(self):
        base = ["item1", "not_needed", "item3"]
        directives = {1: OMIT}
        result = apply_list_directives(base, directives)
        self.assertEqual([x for x in result if x is not OMIT], ["item1", "item3"])

    def test_deep_merge_omit_at_nested_list_index(self):
        base = {"mylist": ["item1", "not_needed", "item3"]}
        updater = {"mylist": {1: OMIT}}
        merged = deep_merge(base, updater)
        self.assertEqual(merged["mylist"], ["item1", "item3"])
