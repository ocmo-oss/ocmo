import yaml
from django.test import TestCase

from core.managers.resolve_parameters import (
    MultilineValue,
    ResolveParametersManager,
    _apply_transformers,
)
from core.managers.resolving import ResolvePipelineManager
from core.managers.secret import SecretManager
from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace

_PEM = "-----BEGIN TEST-----\nline-two\n-----END TEST-----\n"
_SECRET_PEM = "----SECRET----\nAJsndLASndlank\nKJANdnkandiOAI\n---END SECRET--"


class MultilineTransformerTests(TestCase):
    def test_substitute_preserves_newlines_for_full_value_placeholder(self):
        params = {"key": _apply_transformers(_PEM, ["multiline"])}
        self.assertIsInstance(params["key"], MultilineValue)

        result = ResolveParametersManager._substitute("{!key}", params)
        self.assertEqual(result, _PEM)
        self.assertIn("\n", result)

    def test_substitute_preserves_newlines_with_surrounding_whitespace(self):
        params = {"key": _apply_transformers(_PEM, ["multiline"])}
        result = ResolveParametersManager._substitute("{!key}\n", params)
        self.assertEqual(result, _PEM)

    def test_substitute_without_multiline_flattens_newlines(self):
        params = {"key": _PEM}
        result = ResolveParametersManager._substitute("{!key}", params)
        self.assertEqual(result, _PEM.replace("\n", " "))

    def test_substitute_flattens_multiline_for_inline_placeholder(self):
        params = {"key": _apply_transformers(_PEM, ["multiline"])}
        result = ResolveParametersManager._substitute("prefix{!key}suffix", params)
        self.assertEqual(
            result,
            "prefix" + _PEM.replace("\n", " ").replace("\r", " ") + "suffix",
        )

    def _create_secret_and_config(self, config_body: str):
        ns = create_test_namespace(
            f"mlsec{abs(hash(config_body)) % 100000}",
            description="test",
        )
        SecretManager(ns, "app/secret", auth=None).create(_SECRET_PEM)
        TreeManager(ns, "app/cfg", auth=None).create_item(config_body, "config")
        return ns

    def test_resolve_secret_multiline_parameter(self):
        ns = self._create_secret_and_config(
            """\
_ocmo:
  parameters:
    tls_cert:
      type: secret
      value: ./secret
      description: TLS certificate PEM
      transformers:
        - multiline
env:
  - name: TLS_CERT
    value: '{!tls_cert}'
""",
        )

        mgr = ResolvePipelineManager(ns, "app/cfg", "latest")
        outputs = mgr.resolve()
        self.assertEqual(len(outputs), 1)

        data = yaml.safe_load(outputs[0].data_text)
        self.assertEqual(data["env"][0]["value"], _SECRET_PEM)
        self.assertIn("value: |", outputs[0].data_text)
        self.assertNotIn("\\n", outputs[0].data_text)

    def test_resolve_secret_multiline_with_block_scalar_placeholder(self):
        ns = self._create_secret_and_config(
            """\
_ocmo:
  parameters:
    tls_cert:
      type: secret
      value: ./secret
      description: TLS certificate PEM
      transformers:
        - multiline
env:
  - name: TLS_CERT
    value: |
      {!tls_cert}
""",
        )

        mgr = ResolvePipelineManager(ns, "app/cfg", "latest")
        outputs = mgr.resolve()
        data = yaml.safe_load(outputs[0].data_text)
        self.assertEqual(data["env"][0]["value"], _SECRET_PEM)
        self.assertIn("value: |", outputs[0].data_text)
        self.assertNotIn("\\n", outputs[0].data_text)

    def test_resolve_dynamic_multiline_parameter(self):
        ns = create_test_namespace("multilinetest", description="test")
        TreeManager(ns, "app/cfg", auth=None).create_item(
            """\
_ocmo:
  parameters:
    body:
      type: dynamic
      value: ""
      description: Multiline body content
      transformers:
        - multiline
private_key: '{!body}'
""",
            "config",
        )

        mgr = ResolvePipelineManager(
            ns,
            "app/cfg",
            "latest",
            dynamic_params={"body": _PEM},
        )
        outputs = mgr.resolve()
        self.assertEqual(len(outputs), 1)

        data = yaml.safe_load(outputs[0].data_text)
        self.assertEqual(data["private_key"], _PEM)
