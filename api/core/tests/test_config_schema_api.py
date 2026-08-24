"""Tests for config JSON Schema introspection API endpoints."""

from django.test import Client, TestCase, override_settings

from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace

_TEST_MASTER_KEY = "ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs="

_VALID_SCHEMA = """\
_ocmo:
  is_json_schema: true
type: object
properties:
  foo:
    type: string
required:
  - foo
additionalProperties: false
"""

_CONSUMER_VALID = """\
_ocmo:
  validation:
    schema: schemas/app@latest
foo: bar
"""


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ConfigMetadataSchemaEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_returns_ocmo_metadata_json_schema(self):
        response = self.client.get("/api/v1/~config-metadata-schema")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["type"], "object")
        props = data["properties"]
        self.assertIn("extend", props)
        self.assertIn("validation", props)
        self.assertIn("is_json_schema", props)
        validation_props = data["$defs"]["ConfigValidationSchema"]["properties"]
        self.assertIn("schema", validation_props)
        self.assertNotIn("schema_path", validation_props)
        self.assertEqual(validation_props["schema"].get("format"), "uri-reference")

    def test_path_reference_fields_use_uri_reference_format(self):
        response = self.client.get("/api/v1/~config-metadata-schema")
        self.assertEqual(response.status_code, 200, response.content)
        schema = response.json()

        extend_configs = schema["$defs"]["ConfigExtendSchema"]["properties"]["configs"]
        extend_item_formats = [
            item.get("format") for item in extend_configs["items"].get("anyOf", [extend_configs["items"]])
        ]
        self.assertIn("uri-reference", extend_item_formats)

        extend_ref_path = schema["$defs"]["ConfigExtendRefSchema"]["properties"]["path"]
        self.assertEqual(extend_ref_path.get("format"), "uri-reference")

        render_templates = schema["$defs"]["ConfigRenderSchema"]["properties"]["templates"]
        self.assertEqual(render_templates["items"].get("format"), "uri-reference")

        propagation_targets = schema["$defs"]["ConfigPropagationSchema"]["properties"]["targets"]
        self.assertEqual(propagation_targets["items"].get("format"), "uri-reference")

        parameter_transformers = schema["$defs"]["ConfigParameterSchema"]["properties"]["transformers"]
        self.assertEqual(
            set(parameter_transformers["items"]["enum"]),
            {
                "lower",
                "upper",
                "slug",
                "snake",
                "trim",
                "escape_html",
                "b64_encode",
                "urlencode",
                "int",
                "float",
                "bool",
                "null",
                "multiline",
                "omit",
            },
        )

    def test_cast_options_use_format_conditional_schemas(self):
        response = self.client.get("/api/v1/~config-metadata-schema")
        self.assertEqual(response.status_code, 200, response.content)
        schema = response.json()
        cast = schema["$defs"]["CastSchema"]
        options = cast["properties"]["options"]
        self.assertNotIn("properties", options)
        self.assertEqual(options.get("additionalProperties"), False)

        all_of = cast.get("allOf", [])
        yaml_clause = next(
            c for c in all_of if c.get("if", {}).get("properties", {}).get("format", {}).get("const") == "yaml"
        )
        yaml_options_ref = yaml_clause["then"]["properties"]["options"]["$ref"]
        self.assertEqual(yaml_options_ref, "#/$defs/YamlCastOptionsSchema")
        yaml_options = schema["$defs"]["YamlCastOptionsSchema"]["properties"]
        self.assertIn("indent", yaml_options)
        self.assertNotIn("export", yaml_options)

        env_clause = next(
            c for c in all_of if c.get("if", {}).get("properties", {}).get("format", {}).get("const") == "env"
        )
        env_options_ref = env_clause["then"]["properties"]["options"]["$ref"]
        env_options = schema["$defs"][env_options_ref.rsplit("/", 1)[-1]]["properties"]
        self.assertIn("export", env_options)
        self.assertNotIn("indent", env_options)

    def test_parameters_map_declares_value_schema(self):
        response = self.client.get("/api/v1/~config-metadata-schema")
        self.assertEqual(response.status_code, 200, response.content)
        parameters = response.json()["properties"]["parameters"]
        self.assertEqual(
            parameters["additionalProperties"]["$ref"],
            "#/$defs/ConfigParameterSchema",
        )
        self.assertTrue(parameters.get("examples"))
        param = response.json()["$defs"]["ConfigParameterSchema"]
        self.assertIn("description", param["required"])
        self.assertTrue(param["properties"]["description"].get("examples"))

    def test_version_includes_config_metadata_key(self):
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["config_metadata_key"], "_ocmo")


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ConfigDataSchemaEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("cfg-schema-api")
        TreeManager(self.ns, "schemas/app", auth=None).create_item(_VALID_SCHEMA, "config")
        TreeManager(self.ns, "apps/demo", auth=None).create_item(_CONSUMER_VALID, "config")

    def test_consumer_with_validation_schema_returns_schema_body(self):
        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~config-schema/apps/demo")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["type"], "object")
        self.assertIn("foo", data["properties"])

    def test_builtin_permissions_returns_implicit_schema(self):
        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~config-schema/_permissions")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["type"], "object")
        self.assertIn("policies", data["properties"])
        actions = data["properties"]["policies"]["items"]["properties"]["actions"]["items"]
        self.assertIn("lock:read", actions["enum"])
        self.assertIn("lock:write", actions["enum"])
        self.assertIn("lock:delete", actions["enum"])

    def test_plain_config_without_validation_returns_404(self):
        TreeManager(self.ns, "plain/config", auth=None).create_item("key: value\n", "config")
        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~config-schema/plain/config")
        self.assertEqual(response.status_code, 404, response.content)

    def test_schema_config_path_returns_404(self):
        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~config-schema/schemas/app")
        self.assertEqual(response.status_code, 404, response.content)

    def test_missing_config_returns_404(self):
        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~config-schema/does/not/exist")
        self.assertEqual(response.status_code, 404, response.content)
