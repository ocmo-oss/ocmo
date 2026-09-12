"""Unit tests for resolved artifact naming helpers."""

from dataclasses import dataclass

from django.test import SimpleTestCase

from core.utils.output_naming import (
    NameOwnerContext,
    OutputNameError,
    apply_numeric_suffix,
    deduplicate_output_names,
    finalize_output_name,
    resolve_name_template,
    split_name_extension,
    validate_name_template_syntax,
    validate_resolved_name,
)


@dataclass
class _Item:
    name: str


_OWNER = NameOwnerContext(
    path="infra/prod/clusters/eu-cluster",
    name="eu-cluster",
    version_tag="latest",
    version_number=7,
)


class OutputNamingTests(SimpleTestCase):
    def test_split_name_extension(self):
        self.assertEqual(split_name_extension("myconf.yaml"), ("myconf", ".yaml"))
        self.assertEqual(split_name_extension("noext"), ("noext", ""))
        self.assertEqual(split_name_extension(".hidden"), (".hidden", ""))

    def test_apply_numeric_suffix(self):
        self.assertEqual(apply_numeric_suffix("myconf.yaml", 1), "myconf-1.yaml")
        self.assertEqual(apply_numeric_suffix("conf", 2), "conf-2")

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

    def test_resolve_data_placeholder(self):
        name = resolve_name_template("app-{.env}.yaml", {"env": "prod"}, _OWNER)
        self.assertEqual(name, "app-prod.yaml")

    def test_resolve_nested_data_placeholder(self):
        name = resolve_name_template(
            "app-{.database.env}.yaml",
            {"database": {"env": "prod"}},
            _OWNER,
        )
        self.assertEqual(name, "app-prod.yaml")

    def test_resolve_metadata_name_and_path(self):
        name = resolve_name_template(
            "{._ocmo.Name}-{._ocmo.Path[-3]}.conf",
            {},
            _OWNER,
        )
        self.assertEqual(name, "eu-cluster-prod.conf")

    def test_resolve_metadata_version(self):
        name = resolve_name_template(
            "{._ocmo.Version.tag}-{._ocmo.Version.number}.yaml",
            {},
            _OWNER,
        )
        self.assertEqual(name, "latest-7.yaml")

    def test_resolve_mixed_template(self):
        name = resolve_name_template(
            "{._ocmo.Name}-{.overlay.region}.yaml",
            {"overlay": {"region": "eu"}},
            _OWNER,
        )
        self.assertEqual(name, "eu-cluster-eu.yaml")

    def test_missing_data_placeholder_error(self):
        with self.assertRaises(OutputNameError) as ctx:
            resolve_name_template("app-{.env}.yaml", {}, _OWNER)
        self.assertIn("_ocmo.name on infra/prod/clusters/eu-cluster", str(ctx.exception))
        self.assertIn("{.env}", str(ctx.exception))
        self.assertIn("not found in resolved data", str(ctx.exception))

    def test_oob_path_index_error(self):
        with self.assertRaises(OutputNameError) as ctx:
            resolve_name_template("{._ocmo.Path[-9]}.yaml", {}, _OWNER)
        self.assertIn("{._ocmo.Path[-9]}", str(ctx.exception))

    def test_non_scalar_value_error(self):
        with self.assertRaises(OutputNameError) as ctx:
            resolve_name_template("{.labels}.yaml", {"labels": {"a": 1}}, _OWNER)
        self.assertIn("non-scalar", str(ctx.exception))

    def test_validate_resolved_name_rejects_dotdot(self):
        with self.assertRaises(OutputNameError):
            validate_resolved_name("output/../bad.yaml")

    def test_validate_name_template_syntax(self):
        validate_name_template_syntax("{._ocmo.Name}-{.database.env}.yaml")

    def test_finalize_without_template_uses_leaf(self):
        self.assertEqual(
            finalize_output_name(name_template=None, merged_data={}, owner=_OWNER),
            "eu-cluster",
        )

    def test_finalize_with_template(self):
        self.assertEqual(
            finalize_output_name(
                name_template="{._ocmo.Name}.yaml",
                merged_data={},
                owner=_OWNER,
            ),
            "eu-cluster.yaml",
        )
