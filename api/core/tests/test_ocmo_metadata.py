"""Tests for ``_ocmo`` metadata schema validation and limits."""

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from pydantic import ValidationError as PydanticValidationError

from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.schemas.requests import ConfigDocument, ConfigOcmoMetadataSchema
from core.tests.namespace_helpers import create_test_namespace

_TEST_MASTER_KEY = "ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs="


class OcmoMetadataSchemaTests(TestCase):
    def test_extra_top_level_key_rejected(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate({"unknown": True})

    def test_invalid_cast_format_rejected(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "cast": {"format": "exe", "options": {}},
                }
            )

    def test_invalid_cast_option_for_format_rejected(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "cast": {
                        "format": "json",
                        "options": {"uppercase": True},
                    },
                }
            )

    def test_unknown_transformer_rejected(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "parameters": {
                        "env": {
                            "type": "dynamic",
                            "value": "prod",
                            "description": "Environment name",
                            "transformers": ["not_real"],
                        },
                    },
                }
            )

    def test_unused_declared_parameter_rejected(self):
        doc = (
            "_ocmo:\n"
            "  parameters:\n"
            "    env:\n"
            "      type: dynamic\n"
            "      value: prod\n"
            "      description: Environment name\n"
            "key: value\n"
        )
        ns = create_test_namespace("ocmo-unused-param")
        with self.assertRaises(ValidationError):
            TreeManager(ns, "app/unused", auth=None).create_item(doc, "config")

    def test_parameter_referenced_in_metadata_counts_as_used(self):
        doc = (
            "_ocmo:\n"
            "  parameters:\n"
            "    env:\n"
            "      type: dynamic\n"
            "      value: prod\n"
            "      description: Environment name\n"
            "  name: '{!env}'\n"
            "key: value\n"
        )
        validated = ConfigDocument.model_validate(doc)
        self.assertIn("env", validated.root)

    @override_settings(OCMO_MAX_EXTEND_CONFIGS=2)
    def test_extend_reference_limit_enforced(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "extend": {
                        "mode": "accumulate",
                        "configs": ["a@latest", "b@latest", "c@latest"],
                    },
                }
            )


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ExtendRenderIntegrationTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("ocmo-meta")

    def test_extend_distribute_then_render_produces_multiple_outputs(self):
        TreeManager(self.ns, "bases/a", auth=None).create_item("name: a\n", "config")
        TreeManager(self.ns, "bases/b", auth=None).create_item("name: b\n", "config")
        TreeManager(self.ns, "tmpl/out", auth=None).create_item(
            "rendered: {{ name }}\n",
            "template",
        )
        yaml = (
            "_ocmo:\n"
            "  extend:\n"
            "    mode: distribute\n"
            "    configs:\n"
            "      - bases/a@latest\n"
            "      - bases/b@latest\n"
            "  render:\n"
            "    mode: distribute\n"
            "    templates:\n"
            "      - tmpl/out@latest\n"
            "patch:\n"
            "  name: patched\n"
        )
        TreeManager(self.ns, "app/multi", auth=None).create_item(yaml, "config")

        outputs = ResolvePipelineManager(self.ns, "app/multi", "latest", auth=None).resolve()

        self.assertEqual(len(outputs), 2)
        self.assertIn("rendered: a", outputs[0].data_text)
        self.assertIn("rendered: b", outputs[1].data_text)
