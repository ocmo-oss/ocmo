"""Tests for resolver configuration JSON Schema introspection API."""

from django.test import Client, TestCase
from pydantic import ValidationError as PydanticValidationError

from core.schemas.generic import ResolverConfigurationSchema


class ResolverConfigurationSchemaTests(TestCase):
    def test_rejects_include_and_exclude_together(self):
        with self.assertRaises(PydanticValidationError):
            ResolverConfigurationSchema.model_validate(
                {
                    "include": ["*/prod/**"],
                    "exclude": ["**/draft/**"],
                }
            )

    def test_rejects_validate_and_validate_all_together(self):
        with self.assertRaises(PydanticValidationError):
            ResolverConfigurationSchema.model_validate(
                {
                    "validate": "true",
                    "validate_all": "true",
                }
            )

    def test_rejects_reserved_parameter_name(self):
        with self.assertRaises(PydanticValidationError):
            ResolverConfigurationSchema.model_validate(
                {
                    "parameters": {"omit": "x"},
                }
            )

    def test_rejects_invalid_parameter_name(self):
        with self.assertRaises(PydanticValidationError):
            ResolverConfigurationSchema.model_validate(
                {
                    "parameters": {"bad-name": "x"},
                }
            )

    def test_accepts_scalar_parameters(self):
        cfg = ResolverConfigurationSchema.model_validate(
            {
                "parameters": {"replicas": 3, "region": "eu-west-1", "enabled": True},
            }
        )
        self.assertEqual(cfg.parameters["replicas"], 3)


class ResolverConfigurationSchemaEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_returns_resolver_configuration_json_schema(self):
        response = self.client.get("/api/v1/~resolver-configuration-schema")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data.get("title"), "Resolver configuration")
        props = data["properties"]
        self.assertIn("cast", props)
        self.assertIn("parameters", props)
        self.assertIn("include", props)
        self.assertIn("validate", props)

    def test_cast_options_use_format_conditional_schemas(self):
        response = self.client.get("/api/v1/~resolver-configuration-schema")
        self.assertEqual(response.status_code, 200, response.content)
        schema = response.json()
        cast = schema["$defs"]["ResolverCastSchema"]
        options = cast["properties"]["options"]
        self.assertNotIn("properties", options)
        self.assertEqual(options.get("additionalProperties"), False)

        all_of = cast.get("allOf", [])
        yaml_clause = next(
            c for c in all_of if c.get("if", {}).get("properties", {}).get("format", {}).get("const") == "yaml"
        )
        yaml_options_ref = yaml_clause["then"]["properties"]["options"]["$ref"]
        self.assertEqual(yaml_options_ref, "#/$defs/YamlCastOptionsSchema")

    def test_parameters_declare_scalar_value_schema(self):
        response = self.client.get("/api/v1/~resolver-configuration-schema")
        self.assertEqual(response.status_code, 200, response.content)
        parameters = response.json()["properties"]["parameters"]
        self.assertEqual(parameters["propertyNames"]["pattern"], r"^[a-zA-Z_][a-zA-Z0-9_]*$")
        value_types = {branch["type"] for branch in parameters["additionalProperties"]["anyOf"]}
        self.assertEqual(value_types, {"string", "integer", "number", "boolean"})
        self.assertTrue(parameters.get("examples"))
