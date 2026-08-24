from django.test import TestCase

from core.schemas.cast_options import (
    EnvCastOptionsSchema,
    format_cast_options_json_schema,
    validate_cast_options,
)


class CastOptionsSchemaTests(TestCase):
    def test_validate_cast_options_excludes_defaults(self):
        normalized = validate_cast_options("yaml", {})
        self.assertEqual(normalized, {})

        normalized = validate_cast_options("yaml", {"indent": 4})
        self.assertEqual(normalized, {"indent": 4})

    def test_yaml_schema_documents_defaults_and_enums(self):
        schema = format_cast_options_json_schema("yaml")
        indent = schema["properties"]["indent"]
        self.assertEqual(indent["default"], 2)
        self.assertIn("description", indent)
        self.assertIn("examples", indent)

        flow_style = schema["properties"]["flow_style"]
        self.assertEqual(flow_style["enum"], ["block", "flow", "auto"])
        self.assertEqual(flow_style["default"], "block")

    def test_json_schema_flattens_optional_indent(self):
        schema = format_cast_options_json_schema("json")
        indent = schema["properties"]["indent"]
        self.assertNotIn("anyOf", indent)
        self.assertEqual(indent["type"], "integer")
        self.assertIsNone(indent["default"])

    def test_env_schema_documents_dialect_enum(self):
        schema = format_cast_options_json_schema("env")
        dialect = schema["properties"]["type"]
        self.assertEqual(dialect["enum"], ["unix", "windows", "powershell"])
        self.assertEqual(dialect["default"], "unix")
        export = schema["properties"]["export"]
        self.assertEqual(export["x-ocmo-enabled-when"], {"type": "unix"})
        self.assertEqual(
            schema["properties"]["uppercase"]["x-ocmo-incompatible-with"],
            ["lowercase"],
        )

    def test_yaml_schema_has_no_preserve_comments(self):
        schema = format_cast_options_json_schema("yaml")
        self.assertNotIn("preserve_comments", schema["properties"])

    def test_env_uppercase_lowercase_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            EnvCastOptionsSchema.model_validate({"uppercase": True, "lowercase": True})
