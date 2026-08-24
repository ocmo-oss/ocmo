"""Tests for JSONPath-like selector helpers."""

from django.test import SimpleTestCase

from core.shortcuts import (
    SelectorLookupError,
    embed_at_path,
    eval_selector,
    json_path,
    parse_selector,
    validate_selector_syntax,
)


class ParseSelectorTests(SimpleTestCase):
    def test_optional_suffix(self):
        self.assertEqual(parse_selector(".database?"), (".database", True))
        self.assertEqual(parse_selector(".database"), (".database", False))

    def test_invalid_syntax(self):
        with self.assertRaises(ValueError):
            validate_selector_syntax("database")
        with self.assertRaises(ValueError):
            validate_selector_syntax(".bad segment")


class EvalSelectorTests(SimpleTestCase):
    def test_simple_path(self):
        data = {"database": {"aa": "bb"}}
        self.assertEqual(eval_selector(data, ".database"), {"aa": "bb"})

    def test_optional_missing_mapping(self):
        data = {"other": 1}
        self.assertEqual(eval_selector(data, ".database?"), {})

    def test_optional_missing_index(self):
        data = {"items": [{"a": 1}]}
        self.assertEqual(eval_selector(data, ".items[2]?"), [])

    def test_required_missing_raises(self):
        with self.assertRaises(SelectorLookupError) as ctx:
            eval_selector({"a": 1}, ".missing")
        self.assertEqual(ctx.exception.failure_kind, "key")

    def test_json_path_compat(self):
        data = {"a": {"b": [1, 2]}}
        self.assertEqual(json_path(data, ".a.b[1]"), 2)
        self.assertIsNone(json_path(data, ".a.b[9]"))


class EmbedAtPathTests(SimpleTestCase):
    def test_nested_mapping(self):
        self.assertEqual(
            embed_at_path(".persistence.db", {"aa": "bb"}),
            {"persistence": {"db": {"aa": "bb"}}},
        )

    def test_list_index(self):
        self.assertEqual(
            embed_at_path(".services[0].spec", {"port": 8080}),
            {"services": [{"spec": {"port": 8080}}]},
        )

    def test_root_value(self):
        self.assertEqual(embed_at_path(".name", "demo"), {"name": "demo"})
