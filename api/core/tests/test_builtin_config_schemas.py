"""Tests for builtin namespace config JSON Schemas."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from django.test import Client, TestCase, override_settings

from core.constants.permission_actions import (
    PERMISSION_ACTION_PATTERN,
    PERMISSION_ACTIONS,
)
from core.constants.webhook_events import WEBHOOK_EVENTS, WEBHOOK_PAYLOAD_PRESETS
from core.managers.tree import TreeManager
from core.models import Namespace
from core.utils.namespace_special_configs import (
    init_namespace_special_configs,
    sync_permissions_webhooks_schema_configs,
)
from core.utils.permissions_schema_document import build_permissions_schema_document

_TEST_MASTER_KEY = "ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs="

_BUILTIN_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "data" / "builtin_schemas"


def _load_builtin_schema(name: str) -> dict:
    if name == "_permissions.schema":
        return build_permissions_schema_document()
    return yaml.safe_load((_BUILTIN_SCHEMA_DIR / f"{name}.yaml").read_text(encoding="utf-8"))


class BuiltinPermissionsSchemaTests(TestCase):
    def test_actions_enum_matches_pattern_constant(self):
        schema = _load_builtin_schema("_permissions.schema")
        action_items = schema["properties"]["policies"]["items"]["properties"]["actions"]["items"]
        enum_values = action_items["enum"]
        pattern = re.compile(action_items["pattern"])

        self.assertEqual(tuple(enum_values), PERMISSION_ACTIONS)
        self.assertEqual(action_items["pattern"], PERMISSION_ACTION_PATTERN)
        for value in enum_values:
            self.assertRegex(value, pattern)

    def test_actions_enum_excludes_invalid_resource_verb_pairs(self):
        schema = _load_builtin_schema("_permissions.schema")
        enum_values = set(schema["properties"]["policies"]["items"]["properties"]["actions"]["items"]["enum"])
        for invalid in (
            "resolver:tag",
            "resolver:resolve",
            "resolver:describe",
            "lock:audit",
            "lock:tag",
            "lock:resolve",
            "lock:describe",
            "folder:read",
            "template:resolve",
        ):
            self.assertNotIn(invalid, enum_values)
        self.assertIn("template:read", enum_values)
        self.assertIn("folder:audit", enum_values)

    def test_uri_reference_markers(self):
        schema = _load_builtin_schema("_permissions.schema")
        policy_props = schema["properties"]["policies"]["items"]["properties"]

        resolver_actor = policy_props["actors"]["items"]["oneOf"][1]["properties"]["path"]
        self.assertEqual(resolver_actor["format"], "uri-reference")
        self.assertEqual(resolver_actor["x-ocmo-uri-reference"], "resolver")

        resource_items = policy_props["resources"]["items"]
        self.assertEqual(resource_items["format"], "uri-reference")
        self.assertEqual(resource_items["x-ocmo-uri-reference"], "resource")


class BuiltinWebhooksSchemaTests(TestCase):
    def test_events_enum_matches_runtime_events(self):
        schema = _load_builtin_schema("_webhooks.schema")
        event_items = schema["properties"]["webhooks"]["items"]["properties"]["events"]["items"]
        self.assertEqual(tuple(event_items["enum"]), WEBHOOK_EVENTS)

    def test_payload_presets_enum(self):
        schema = _load_builtin_schema("_webhooks.schema")
        preset = schema["properties"]["webhooks"]["items"]["properties"]["payload"]["properties"]["preset"]
        self.assertEqual(tuple(preset["enum"]), WEBHOOK_PAYLOAD_PRESETS)


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class BuiltinSchemaApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ns = Namespace.objects.create(name="builtin-schema-api", description="test")
        init_namespace_special_configs(cls.ns)
        cls.client = Client()

    def test_permissions_schema_endpoint_includes_action_enum(self):
        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~config-schema/_permissions")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        actions = data["properties"]["policies"]["items"]["properties"]["actions"]["items"]
        self.assertIn("config:read", actions["enum"])
        self.assertIn("lock:read", actions["enum"])
        self.assertIn("lock:write", actions["enum"])
        self.assertIn("lock:delete", actions["enum"])
        self.assertIn("*:audit", actions["enum"])
        self.assertIn("*:*", actions["enum"])
        self.assertNotIn("lock:tag", actions["enum"])
        self.assertNotIn("resolver:tag", actions["enum"])
        self.assertEqual(
            data["properties"]["policies"]["items"]["properties"]["resources"]["items"]["format"],
            "uri-reference",
        )

    def test_permissions_schema_endpoint_patches_stale_db_enum(self):
        stale_schema = build_permissions_schema_document()
        stale_actions = stale_schema["properties"]["policies"]["items"]["properties"]["actions"]["items"]
        stale_actions["enum"] = list(stale_actions["enum"]) + ["lock:tag", "resolver:tag"]
        TreeManager(self.ns, "_permissions.schema", auth=None).update_item(
            yaml.safe_dump(stale_schema, sort_keys=False)
        )

        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~config-schema/_permissions")
        self.assertEqual(response.status_code, 200, response.content)
        enum_values = response.json()["properties"]["policies"]["items"]["properties"]["actions"]["items"]["enum"]
        self.assertEqual(tuple(enum_values), PERMISSION_ACTIONS)

    def test_webhooks_schema_endpoint_includes_event_enum(self):
        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~config-schema/_webhooks")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        events = data["properties"]["webhooks"]["items"]["properties"]["events"]["items"]
        self.assertIn("config.created", events["enum"])
        self.assertIn("propagation.triggered", events["enum"])

    def test_fresh_namespace_has_updated_builtin_schemas(self):
        ns = Namespace.objects.create(name="schema-fresh-ns", description="schema test")
        init_namespace_special_configs(ns)
        schema_mgr = TreeManager(ns, "_permissions.schema", auth=None)
        _, body = schema_mgr.load_config_version_document("latest")
        actions = body["properties"]["policies"]["items"]["properties"]["actions"]["items"]
        self.assertGreaterEqual(len(actions["enum"]), 35)
        self.assertIn("lock:read", actions["enum"])
        self.assertIn("lock:write", actions["enum"])
        self.assertIn("lock:delete", actions["enum"])

    def test_sync_updates_stale_permissions_and_webhooks_schemas(self):
        ns = Namespace.objects.create(name="schema-sync-ns", description="sync test")
        init_namespace_special_configs(ns)

        stale_permissions_schema = """\
_ocmo:
  is_json_schema: true
type: object
properties:
  policies:
    type: array
"""
        TreeManager(ns, "_permissions.schema", auth=None).update_item(stale_permissions_schema)

        updated = sync_permissions_webhooks_schema_configs(ns)
        self.assertEqual(updated, ["_permissions.schema"])

        response = self.client.get(f"/api/v1/ns/{ns.name}/~config-schema/_permissions")
        self.assertEqual(response.status_code, 200, response.content)
        actions = response.json()["properties"]["policies"]["items"]["properties"]["actions"]["items"]
        self.assertIn("lock:read", actions["enum"])
        self.assertIn("lock:write", actions["enum"])
        self.assertIn("lock:delete", actions["enum"])
        self.assertIn("*:*", actions["enum"])

        # Idempotent: packaged content already applied.
        self.assertEqual(sync_permissions_webhooks_schema_configs(ns), [])
