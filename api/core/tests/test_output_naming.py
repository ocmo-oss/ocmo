"""Unit tests for resolved artifact naming helpers."""

from dataclasses import dataclass

from django.test import SimpleTestCase

from core.utils.output_naming import (
    apply_numeric_suffix,
    deduplicate_output_names,
    replicate_output_name,
    split_name_extension,
)


@dataclass
class _Item:
    name: str


class OutputNamingTests(SimpleTestCase):
    def test_split_name_extension(self):
        self.assertEqual(split_name_extension("myconf.yaml"), ("myconf", ".yaml"))
        self.assertEqual(split_name_extension("noext"), ("noext", ""))
        self.assertEqual(split_name_extension(".hidden"), (".hidden", ""))

    def test_apply_numeric_suffix(self):
        self.assertEqual(apply_numeric_suffix("myconf.yaml", 1), "myconf-1.yaml")
        self.assertEqual(apply_numeric_suffix("conf", 2), "conf-2")

    def test_replicate_output_name(self):
        self.assertEqual(replicate_output_name("myconf.yaml", 1), "myconf-1.yaml")
        self.assertEqual(replicate_output_name("myconf.yaml", 3), "myconf-3.yaml")

    def test_deduplicate_output_names_keeps_first(self):
        items = [_Item("conf.yaml"), _Item("conf.yaml"), _Item("conf.yaml")]
        deduplicate_output_names(items)
        self.assertEqual([i.name for i in items], ["conf.yaml", "conf-1.yaml", "conf-2.yaml"])

    def test_deduplicate_output_names_single_output_noop(self):
        items = [_Item("conf.yaml")]
        deduplicate_output_names(items)
        self.assertEqual(items[0].name, "conf.yaml")

    def test_deduplicate_output_names_already_unique(self):
        items = [_Item("a.yaml"), _Item("b.yaml")]
        deduplicate_output_names(items)
        self.assertEqual([i.name for i in items], ["a.yaml", "b.yaml"])
