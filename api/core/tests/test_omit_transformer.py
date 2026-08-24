import yaml
from django.test import TestCase

from core.constants.resolve import OMIT
from core.managers.resolve_parameters import (
    ResolveParametersManager,
    _apply_transformers,
)
from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace
from core.utils.deep_merge import strip_omit


class OmitTransformerTests(TestCase):
    def test_omit_transformer_maps_empty_to_omit_sentinel(self):
        self.assertIs(_apply_transformers("", ["omit"]), OMIT)
        self.assertIs(_apply_transformers(None, ["omit"]), OMIT)
        self.assertEqual(_apply_transformers("hello", ["omit"]), "hello")

    def test_substitute_removes_dict_key_for_omitted_parameter(self):
        params = {"opt": _apply_transformers("", ["omit"])}
        body = {"keep": "yes", "optional": "{!opt}", "also": "here"}
        substituted = ResolveParametersManager._substitute(body, params)
        result = strip_omit(substituted)
        self.assertEqual(result, {"keep": "yes", "also": "here"})

    def test_resolve_dynamic_omit_parameter_removes_property(self):
        ns = create_test_namespace("omitparamtest", description="test")
        TreeManager(ns, "app/cfg", auth=None).create_item(
            """\
_ocmo:
  parameters:
    optional:
      type: dynamic
      value: ""
      description: Optional value omitted when empty
      transformers:
        - omit
keep: kept
optional: '{!optional}'
also: stays
""",
            "config",
        )

        mgr = ResolvePipelineManager(ns, "app/cfg", "latest")
        outputs = mgr.resolve()
        data = yaml.safe_load(outputs[0].data_text)
        self.assertEqual(data, {"keep": "kept", "also": "stays"})
        self.assertNotIn("optional", outputs[0].data_text)

    def test_resolve_dynamic_omit_parameter_keeps_property_when_set(self):
        ns = create_test_namespace("omitparamset", description="test")
        TreeManager(ns, "app/cfg", auth=None).create_item(
            """\
_ocmo:
  parameters:
    optional:
      type: dynamic
      value: ""
      description: Optional value omitted when empty
      transformers:
        - omit
optional: '{!optional}'
""",
            "config",
        )

        mgr = ResolvePipelineManager(
            ns,
            "app/cfg",
            "latest",
            dynamic_params={"optional": "present"},
        )
        outputs = mgr.resolve()
        data = yaml.safe_load(outputs[0].data_text)
        self.assertEqual(data["optional"], "present")
