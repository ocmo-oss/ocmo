import yaml
from django.test import Client, TestCase

from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.schemas.requests import TagPayload
from core.tests.namespace_helpers import create_test_namespace
from core.utils.permissions_compiler import PermissionsCompiler

_VERSION_PARAMS_YAML = """\
_ocmo:
  parameters:
    version_tag:
      type: projected
      value: .Version.tag
      description: Version reference used to resolve this config
    version_number:
      type: projected
      value: .Version.number
      description: Resolved integer version number
build: "{!version_tag}-v{!version_number}"
"""


class ResolveParametersVersionTests(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        self.client = Client()
        self.ns = create_test_namespace("versionparamtest", description="test")
        self._create_config("app/cfg", "key: one\n")
        self._update_config("app/cfg", _VERSION_PARAMS_YAML)
        TreeManager(self.ns, "app/cfg", auth=None).set_item_tag(TagPayload(tag="release", version=2))
        TreeManager(self.ns, "app/cfg", auth=None).promote_stable_tag(2)

    def _create_config(self, path: str, body: str):
        TreeManager(self.ns, path, auth=None).create_item(body, "config")

    def _update_config(self, path: str, body: str):
        TreeManager(self.ns, path, auth=None).update_item(body)

    def _resolve_parameters(self, path: str, **params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"/api/v1/ns/{self.ns.name}/~resolve-parameters/{path}"
        if query:
            url = f"{url}?{query}"
        return self.client.get(url)

    def test_projected_version_tag_from_custom_tag(self):
        response = self._resolve_parameters("app/cfg", version="release")
        self.assertEqual(response.status_code, 200, response.content)

        params = response.json()["parameters"]
        self.assertEqual(params["version_tag"]["raw_value"], "release")
        self.assertEqual(params["version_tag"]["effective_value"], "release")
        self.assertEqual(response.json()["version"], 2)
        self.assertEqual(response.json()["requested_version"], "release")

    def test_projected_version_number_from_latest(self):
        response = self._resolve_parameters("app/cfg", version="latest")
        self.assertEqual(response.status_code, 200, response.content)

        params = response.json()["parameters"]
        self.assertEqual(params["version_number"]["raw_value"], 2)
        self.assertEqual(params["version_number"]["effective_value"], 2)

    def test_projected_version_numeric_ref(self):
        response = self._resolve_parameters("app/cfg", version="2")
        self.assertEqual(response.status_code, 200, response.content)

        params = response.json()["parameters"]
        self.assertEqual(params["version_tag"]["raw_value"], "2")
        self.assertEqual(params["version_tag"]["effective_value"], "2")
        self.assertEqual(params["version_number"]["raw_value"], 2)
        self.assertEqual(params["version_number"]["effective_value"], 2)

    def test_resolve_substitutes_version_parameters(self):
        mgr = ResolvePipelineManager(self.ns, "app/cfg", "stable")
        outputs = mgr.resolve()
        self.assertEqual(len(outputs), 1)

        data = yaml.safe_load(outputs[0].data_text)
        self.assertEqual(data["build"], "stable-v2")

    def test_extend_chain_uses_per_config_version_tag(self):
        self._create_config(
            "shared/base",
            """\
_ocmo:
  parameters:
    version_tag:
      type: projected
      value: .Version.tag
      description: Version tag from config metadata
tag: "{!version_tag}"
""",
        )
        TreeManager(self.ns, "shared/base", auth=None).promote_stable_tag(1)

        self._create_config(
            "app/root",
            """\
_ocmo:
  parameters:
    version_tag:
      type: projected
      value: .Version.tag
      description: Version tag from config metadata
  extend:
    configs:
      - ../shared/base@stable
    mode: accumulate
root_tag: "{!version_tag}"
""",
        )

        root_mgr = ResolvePipelineManager(self.ns, "app/root", "latest")
        outputs = root_mgr.resolve()
        self.assertEqual(len(outputs), 1)

        data = yaml.safe_load(outputs[0].data_text)
        self.assertEqual(data["root_tag"], "latest")
        self.assertEqual(data["tag"], "stable")

        base_debug = self._resolve_parameters("shared/base", version="stable")
        self.assertEqual(
            base_debug.json()["parameters"]["version_tag"]["effective_value"],
            "stable",
        )

    def test_null_transformer_emits_explicit_yaml_null(self):
        self._create_config(
            "app/nullable",
            """\
_ocmo:
  parameters:
    optional:
      type: dynamic
      value: ""
      description: Optional value coerced to null
      transformers:
        - "null"
optional: '{!optional}'
""",
        )

        mgr = ResolvePipelineManager(self.ns, "app/nullable", "latest")
        outputs = mgr.resolve()
        self.assertEqual(len(outputs), 1)
        self.assertIn("optional: null", outputs[0].data_text)

        data = yaml.safe_load(outputs[0].data_text)
        self.assertIsNone(data["optional"])

    def test_null_transformer_preserves_nonempty_string(self):
        self._create_config(
            "app/nullable-set",
            """\
_ocmo:
  parameters:
    optional:
      type: dynamic
      value: ""
      description: Optional value coerced to null when empty
      transformers:
        - "null"
optional: '{!optional}'
""",
        )

        mgr = ResolvePipelineManager(
            self.ns,
            "app/nullable-set",
            "latest",
            dynamic_params={"optional": "hello"},
        )
        outputs = mgr.resolve()
        self.assertEqual(len(outputs), 1)
        self.assertIn("optional: hello", outputs[0].data_text)

        data = yaml.safe_load(outputs[0].data_text)
        self.assertEqual(data["optional"], "hello")
