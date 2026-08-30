"""Tests for Config JSON Schema validation on create/update."""

from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import PermissionDenied
from core.managers.auth import AuthManager
from core.managers.config_validation import ConfigValidationManager
from core.managers.tree import TreeManager
from core.models import GlobalPermissionRule, Namespace
from core.schemas.requests import ConfigOcmoMetadataSchema, TagPayload
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

_INVALID_SCHEMA_BODY = """\
_ocmo:
  is_json_schema: true
type: not-a-valid-type
"""

_CONSUMER_VALID = """\
_ocmo:
  validation:
    schema: schemas/app@latest
foo: bar
"""

_CONSUMER_INVALID_DATA = """\
_ocmo:
  validation:
    schema: schemas/app@latest
foo: 123
"""

_NON_SCHEMA_TARGET = """\
key: value
"""


from core.utils.namespace_special_configs import init_namespace_special_configs


def _init_namespace(name: str) -> Namespace:
    ns = Namespace.objects.create(name=name, description="test")
    init_namespace_special_configs(ns)
    return ns


def _grant_namespace_write(email: str, pattern: str = "*"):
    GlobalPermissionRule.objects.create(
        position=1.0,
        rule={
            "namespace": pattern,
            "write": {"actors": [{"kind": "User", "claims": {"email": email}}]},
        },
    )


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ConfigValidationSchemaTests(TestCase):
    def test_is_json_schema_exclusive_with_extend(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "is_json_schema": True,
                    "extend": {"mode": "accumulate", "configs": ["a@latest"]},
                }
            )

    def test_is_json_schema_exclusive_with_validation(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "is_json_schema": True,
                    "validation": {"schema": "schemas/x@latest"},
                }
            )

    def test_invalid_json_schema_body_rejected_on_create(self):
        ns = _init_namespace("cfg-val-schema-syntax")
        with self.assertRaises(ValidationError):
            TreeManager(ns, "schemas/bad", auth=None).create_item(_INVALID_SCHEMA_BODY, "config")


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ConfigValidationManagerTests(TestCase):
    def setUp(self):
        self.ns = _init_namespace("cfg-val-test")

    def test_schema_config_create_and_consumer_validate_success(self):
        TreeManager(self.ns, "schemas/app", auth=None).create_item(_VALID_SCHEMA, "config")
        TreeManager(self.ns, "apps/demo", auth=None).create_item(_CONSUMER_VALID, "config")

    def test_consumer_rejects_invalid_data(self):
        TreeManager(self.ns, "schemas/app", auth=None).create_item(_VALID_SCHEMA, "config")
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "apps/demo", auth=None).create_item(_CONSUMER_INVALID_DATA, "config")

    def test_validation_schema_requires_is_json_schema_flag(self):
        TreeManager(self.ns, "schemas/plain", auth=None).create_item(_NON_SCHEMA_TARGET, "config")
        doc = """\
_ocmo:
  validation:
    schema: schemas/plain@latest
foo: bar
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "apps/bad-ref", auth=None).create_item(doc, "config")

    def test_missing_schema_config_rejected(self):
        doc = """\
_ocmo:
  validation:
    schema: schemas/missing@latest
foo: bar
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "apps/missing", auth=None).create_item(doc, "config")

    def test_builtin_permissions_validated_without_explicit_validation(self):
        TreeManager(self.ns, "_permissions", auth=None).update_item("policies: []\n")

    def test_builtin_permissions_invalid_data_rejected(self):
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "_permissions", auth=None).update_item("policies: not-a-list\n")

    def test_builtin_permissions_cannot_declare_validation(self):
        doc = """\
_ocmo:
  validation:
    schema: _permissions.schema@latest
policies: []
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "_permissions", auth=None).update_item(doc)

    def test_builtin_permissions_rejects_oversized_resource_glob(self):
        doc = f"""\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "*"
    actions:
      - config:read
    resources:
      - {"a" * 513}
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "_permissions", auth=None).update_item(doc)

    def test_builtin_permissions_rejects_resolver_placeholder_in_claims(self):
        doc = """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "{!resolver.name}"
    actions:
      - config:read
    resources:
      - "**"
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "_permissions", auth=None).update_item(doc)

    def test_builtin_permissions_rejects_unknown_action(self):
        doc = """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "*"
    actions:
      - config:foo
    resources:
      - "**"
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "_permissions", auth=None).update_item(doc)

    def test_builtin_permissions_rejects_user_actor_without_claims(self):
        doc = """\
policies:
  - effect: Allow
    actors:
      - kind: User
    actions:
      - config:read
    resources:
      - "**"
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "_permissions", auth=None).update_item(doc)

    def test_builtin_permissions_rejects_malformed_time_of_day(self):
        doc = """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "*"
    actions:
      - config:read
    resources:
      - "**"
    conditions:
      time_of_day:
        - "9:00-17:00"
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "_permissions", auth=None).update_item(doc)

    def test_builtin_permissions_accepts_resolver_actor_with_path(self):
        doc = """\
policies:
  - effect: Allow
    actors:
      - kind: Resolver
        path: app/svc
    actions:
      - config:resolve
    resources:
      - shared/**
"""
        TreeManager(self.ns, "_permissions", auth=None).update_item(doc)

    def test_relative_schema_path_resolved(self):
        TreeManager(self.ns, "project/schemas/app", auth=None).create_item(_VALID_SCHEMA, "config")
        doc = """\
_ocmo:
  validation:
    schema: ../schemas/app@latest
foo: bar
"""
        TreeManager(self.ns, "project/apps/demo", auth=None).create_item(doc, "config")

    def test_schema_version_pin(self):
        TreeManager(self.ns, "schemas/app", auth=None).create_item(_VALID_SCHEMA, "config")
        TreeManager(self.ns, "schemas/app", auth=None).update_item(
            """\
_ocmo:
  is_json_schema: true
type: object
properties:
  foo:
    type: integer
required:
  - foo
additionalProperties: false
"""
        )
        TreeManager(self.ns, "schemas/app", auth=None).promote_stable_tag(1)
        doc_v1 = """\
_ocmo:
  validation:
    schema: schemas/app@1
foo: bar
"""
        TreeManager(self.ns, "apps/pinned", auth=None).create_item(doc_v1, "config")
        doc_latest = """\
_ocmo:
  validation:
    schema: schemas/app@latest
foo: bar
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "apps/latest", auth=None).create_item(doc_latest, "config")


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class BuiltinSchemaConfigTests(TestCase):
    def setUp(self):
        self.ns = _init_namespace("builtin-schema-test")

    def test_builtin_schema_paths_created(self):
        for path in ("_permissions.schema", "_webhooks.schema", "_git_sync.schema"):
            item = TreeManager(self.ns, path, auth=None).get_or_raise(["config"])
            self.assertIsNotNone(item)

    def test_builtin_schema_config_not_writable(self):
        _grant_namespace_write("writer@example.com")
        auth = AuthManager({"_type": "user", "email": "writer@example.com"})
        with self.assertRaises(PermissionDenied):
            TreeManager(self.ns, "_permissions.schema", auth=auth).update_item(_VALID_SCHEMA)


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ConfigValidationApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("cfg-val-api")
        TreeManager(self.ns, "schemas/app", auth=None).create_item(_VALID_SCHEMA, "config")

    def test_api_rejects_invalid_ocmo_metadata(self) -> None:
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/apps/bad-meta",
            data=b"_ocmo:\n  is_json_schema: blabla\n",
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 422, response.content)
        payload = response.json()
        self.assertIn("_ocmo.is_json_schema", payload["error"][0])
        self.assertNotIn("errors.pydantic.dev", payload["error"][0])

    def test_api_rejects_invalid_consumer_data(self):
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/apps/demo",
            data=_CONSUMER_INVALID_DATA.encode(),
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 422, response.content)

    def test_api_accepts_valid_consumer_data(self):
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/apps/demo",
            data=_CONSUMER_VALID.encode(),
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_scalar_config_without_ocmo_succeeds(self):
        TreeManager(self.ns, "scalars/plain", auth=None).create_item(
            "plain text value\n",
            "config",
        )


class ConfigValidationParseTests(TestCase):
    def test_parse_invalid_ocmo_metadata_returns_field_messages(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            ConfigValidationManager.parse_config_yaml_document("_ocmo:\n  is_json_schema: blabla\n")
        messages = ctx.exception.messages
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            messages[0],
            "_ocmo.is_json_schema: Input should be a valid boolean, unable to interpret input",
        )

    def test_parse_dict_with_ocmo(self):
        metadata, body = ConfigValidationManager.parse_config_yaml_document(
            {
                "_ocmo": {"name": "demo"},
                "foo": "bar",
            }
        )
        self.assertEqual(metadata.name, "demo")
        self.assertEqual(body, {"foo": "bar"})

    def test_parse_scalar_root(self):
        metadata, body = ConfigValidationManager.parse_config_yaml_document("plain scalar\n")
        self.assertEqual(metadata.name, None)
        self.assertFalse(metadata.is_json_schema)
        self.assertEqual(body, "plain scalar")

    def test_parse_sequence_root(self):
        metadata, body = ConfigValidationManager.parse_config_yaml_document("- one\n- two\n")
        self.assertEqual(metadata.name, None)
        self.assertFalse(metadata.is_json_schema)
        self.assertEqual(body, ["one", "two"])


class ConfigReferenceValidationTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("cfg-ref-val")

    def test_save_validates_extend_path_after_substituting_dynamic_default(self):
        TreeManager(self.ns, "bases/prod", auth=None).create_item("tier: prod\n", "config")
        TreeManager(self.ns, "app/root", auth=None).create_item(
            """\
_ocmo:
  parameters:
    env:
      type: dynamic
      value: prod
      description: Environment name
  extend:
    configs:
      - path: ../bases/{!env}
        key: .tier
    mode: accumulate
value: ok
""",
            "config",
        )

    def test_save_validates_extend_tag_after_substituting_dynamic_default(self):
        TreeManager(self.ns, "shared/images", auth=None).create_item("registry: pinned\n", "config")
        TreeManager(self.ns, "shared/images", auth=None).set_item_tag(TagPayload(tag="pinned", version=1))
        TreeManager(self.ns, "app/overlay", auth=None).create_item(
            """\
_ocmo:
  parameters:
    image_tag:
      type: dynamic
      value: pinned
      description: Image config tag
  extend:
    configs:
      - ../shared/images@{!image_tag}
    mode: accumulate
value: ok
""",
            "config",
        )

    def test_save_rejects_extend_when_default_resolves_to_missing_config(self):
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "app/root", auth=None).create_item(
                """\
_ocmo:
  parameters:
    env:
      type: dynamic
      value: missing
      description: Environment name
  extend:
    configs:
      - ../bases/{!env}
    mode: accumulate
value: ok
""",
                "config",
            )

    def test_save_rejects_extend_when_default_tag_missing_on_target(self):
        TreeManager(self.ns, "shared/images", auth=None).create_item("registry: latest\n", "config")
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "app/overlay", auth=None).create_item(
                """\
_ocmo:
  parameters:
    image_tag:
      type: dynamic
      value: pinned
      description: Image config tag
  extend:
    configs:
      - ../shared/images@{!image_tag}
    mode: accumulate
value: ok
""",
                "config",
            )

    def test_save_validates_extend_with_projected_path_segment(self):
        TreeManager(self.ns, "bases/prod", auth=None).create_item("tier: prod\n", "config")
        TreeManager(self.ns, "apps/payments/prod/release", auth=None).create_item(
            """\
_ocmo:
  parameters:
    env:
      type: projected
      value: .Path[-2]
      description: Environment segment
  extend:
    configs:
      - ../../../bases/{!env}
    mode: accumulate
value: ok
""",
            "config",
        )
