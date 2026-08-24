"""Tests for POST /auth/can-i/ permission probe endpoint."""

import json
from contextlib import contextmanager
from unittest.mock import patch

from django.test import Client, TestCase

from core.managers.auth import AuthManager
from core.models import GlobalPermissionRule
from core.tests.auth_helpers import authenticated_as, deny_authentication
from core.tests.namespace_helpers import create_test_namespace
from core.utils.permissions_compiler import PermissionsCompiler


@contextmanager
def _authenticated_request(user=None):
    with authenticated_as(user):
        yield


def _post_can_i(client, payload, *, user=None, authenticate=True):
    if not authenticate:
        with deny_authentication():
            return client.post(
                "/api/v1/auth/can-i/",
                data=json.dumps(payload),
                content_type="application/json",
            )
    with _authenticated_request(user):
        return client.post(
            "/api/v1/auth/can-i/",
            data=json.dumps(payload),
            content_type="application/json",
        )


class TestProbePermissions(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.ns = create_test_namespace("can-i-test")

    def tearDown(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def _user_auth(self, **claims):
        return AuthManager({"_type": "user", **claims})

    def test_global_admin_allowed(self):
        auth = self._user_auth(email="admin@example.com")
        result = auth.probe_permissions(["global:admin"])
        self.assertTrue(result["global:admin"])

    def test_global_admin_denied(self):
        auth = self._user_auth(groups="other")
        result = auth.probe_permissions(["global:admin"])
        self.assertFalse(result["global:admin"])

    def test_namespace_read_allowed(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "can-i-*",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "bob@example.com"}}]},
                }
            ]
        )
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            result = auth.probe_permissions(
                ["namespace:read"],
                namespace_name=self.ns.name,
            )
        self.assertTrue(result["namespace:read"])

    def test_namespace_read_denied(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "can-i-*",
                    "read": {"actors": [{"kind": "User", "claims": {"groups": "special"}}]},
                }
            ]
        )
        auth = self._user_auth(email="bob@example.com", groups="other")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            result = auth.probe_permissions(
                ["namespace:read"],
                namespace_name=self.ns.name,
            )
        self.assertFalse(result["namespace:read"])

    def test_namespace_read_without_namespace_name(self):
        auth = self._user_auth(email="bob@example.com")
        result = auth.probe_permissions(["namespace:read"])
        self.assertFalse(result["namespace:read"])

    def test_tree_op_allowed(self):
        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    {
                        "effect": "Allow",
                        "actors": [{"kind": "User", "claims": {"email": "*"}}],
                        "actions": ["config:read"],
                        "resources": ["**"],
                    }
                ]
            }
        )
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            result = auth.probe_permissions(
                ["config:read"],
                namespace_name=self.ns.name,
                namespace=self.ns,
                resource="app/cfg",
            )
        self.assertTrue(result["config:read"])

    def test_tree_op_denied(self):
        ps = PermissionsCompiler.compile_policy_set({"policies": []})
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            result = auth.probe_permissions(
                ["config:read"],
                namespace_name=self.ns.name,
                namespace=self.ns,
                resource="app/cfg",
            )
        self.assertFalse(result["config:read"])

    def test_tree_op_without_resource(self):
        auth = self._user_auth(email="bob@example.com")
        result = auth.probe_permissions(
            ["config:read"],
            namespace_name=self.ns.name,
            namespace=self.ns,
        )
        self.assertFalse(result["config:read"])

    def test_lock_list_read_with_empty_resource(self):
        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    {
                        "effect": "Allow",
                        "actors": [{"kind": "User", "claims": {"email": "*"}}],
                        "actions": ["lock:read"],
                        "resources": ["**"],
                    }
                ]
            }
        )
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            result = auth.probe_permissions(
                ["lock:read"],
                namespace_name=self.ns.name,
                namespace=self.ns,
                resource="",
            )
        self.assertTrue(result["lock:read"])

    def test_lock_list_read_denied_with_empty_resource(self):
        ps = PermissionsCompiler.compile_policy_set({"policies": []})
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            result = auth.probe_permissions(
                ["lock:read"],
                namespace_name=self.ns.name,
                namespace=self.ns,
                resource="",
            )
        self.assertFalse(result["lock:read"])

    def test_namespace_create_allowed_when_any_write_rule_matches(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "team-*",
                    "write": {"actors": [{"kind": "User", "claims": {"email": "bob@example.com"}}]},
                }
            ]
        )
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            result = auth.probe_permissions(["namespace:create"])
        self.assertTrue(result["namespace:create"])

    def test_namespace_create_denied_without_write_rule(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "team-*",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "bob@example.com"}}]},
                }
            ]
        )
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            result = auth.probe_permissions(["namespace:create"])
        self.assertFalse(result["namespace:create"])

    def test_tree_op_without_namespace_object(self):
        auth = self._user_auth(email="bob@example.com")
        result = auth.probe_permissions(
            ["config:read"],
            namespace_name="missing-ns",
            resource="app/cfg",
        )
        self.assertFalse(result["config:read"])

    def test_namespace_read_on_missing_namespace_still_evaluates_global_rules(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "missing-*",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "bob@example.com"}}]},
                }
            ]
        )
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            result = auth.probe_permissions(
                ["namespace:read"],
                namespace_name="missing-ns",
            )
        self.assertTrue(result["namespace:read"])

    def test_batch_multiple_operations(self):
        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    {
                        "effect": "Allow",
                        "actors": [{"kind": "User", "claims": {"email": "*"}}],
                        "actions": ["config:resolve"],
                        "resources": ["**"],
                    }
                ]
            }
        )
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "can-i-*",
                    "write": {"actors": [{"kind": "User", "claims": {"email": "bob@example.com"}}]},
                }
            ]
        )
        auth = self._user_auth(email="bob@example.com", groups="other")
        with (
            patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps),
            patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled),
        ):
            result = auth.probe_permissions(
                ["config:resolve", "secret:tag", "namespace:write", "global:admin"],
                namespace_name=self.ns.name,
                namespace=self.ns,
                resource="app/cfg",
            )
        self.assertTrue(result["config:resolve"])
        self.assertFalse(result["secret:tag"])
        self.assertTrue(result["namespace:write"])
        self.assertFalse(result["global:admin"])


class TestCanIEndpoint(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.client = Client()
        self.ns = create_test_namespace("can-i-endpoint")

    def tearDown(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def test_tree_op_allowed_for_authenticated_user(self):
        response = _post_can_i(
            self.client,
            {
                "namespace": self.ns.name,
                "operations": ["config:read"],
                "resource": "app/cfg",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["allowed"]["config:read"])

    def test_wildcard_audit_probe_grants_typed_item_audit(self):
        from core.managers.tree import TreeManager

        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "can-i-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "auditor@example.com"}}]},
            },
        )
        PermissionsCompiler._global_cache.clear()
        PermissionsCompiler._policy_cache.clear()
        TreeManager(self.ns, "_permissions", auth=None).update_item(
            "policies:\n"
            "  - effect: Allow\n"
            "    actors:\n"
            "      - kind: User\n"
            "        claims:\n"
            "          email: auditor@example.com\n"
            "    actions:\n"
            "      - '*:audit'\n"
            "    resources:\n"
            "      - '**'\n"
        )
        PermissionsCompiler._policy_cache.clear()
        user = {
            "_type": "user",
            "sub": "auditor",
            "email": "auditor@example.com",
            "name": "Auditor",
            "groups": "other",
        }
        response = _post_can_i(
            self.client,
            {
                "namespace": self.ns.name,
                "operations": ["config:audit", "folder:audit", "resolver:audit"],
                "resource": "app/cfg",
            },
            user=user,
        )
        self.assertEqual(response.status_code, 200, response.content)
        allowed = response.json()["allowed"]
        self.assertTrue(allowed["config:audit"])
        self.assertTrue(allowed["folder:audit"])
        self.assertTrue(allowed["resolver:audit"])

    def test_tree_op_denied_with_empty_policy(self):
        ps = PermissionsCompiler.compile_policy_set({"policies": []})
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            response = _post_can_i(
                self.client,
                {
                    "namespace": self.ns.name,
                    "operations": ["config:read"],
                    "resource": "app/cfg",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["allowed"]["config:read"])

    def test_namespace_read_allowed(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "can-i-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
            },
        )
        response = _post_can_i(
            self.client,
            {
                "namespace": self.ns.name,
                "operations": ["namespace:read"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["allowed"]["namespace:read"])

    def test_namespace_read_denied(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "can-i-*",
                "read": {"actors": [{"kind": "User", "claims": {"groups": "special"}}]},
            },
        )
        auth = AuthManager(
            {
                "_type": "user",
                "sub": "bob",
                "email": "bob@example.com",
                "name": "Bob",
                "groups": "other",
            }
        )
        response = _post_can_i(
            self.client,
            {
                "namespace": self.ns.name,
                "operations": ["namespace:read"],
            },
            user=auth._raw,
        )
        self.assertEqual(response.status_code, 404)

    def test_global_admin_allowed(self):
        response = _post_can_i(
            self.client,
            {
                "operations": ["global:admin"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["allowed"]["global:admin"])

    def test_global_admin_denied(self):
        user = {
            "_type": "user",
            "sub": "bob",
            "email": "bob@example.com",
            "name": "Bob",
            "groups": "other",
        }
        response = _post_can_i(
            self.client,
            {
                "operations": ["global:admin"],
            },
            user=user,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["allowed"]["global:admin"])

    def test_missing_namespace_returns_false_for_tree_ops(self):
        response = _post_can_i(
            self.client,
            {
                "operations": ["config:read"],
                "resource": "app/cfg",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["allowed"]["config:read"])

    def test_missing_resource_returns_false_for_tree_ops(self):
        response = _post_can_i(
            self.client,
            {
                "namespace": self.ns.name,
                "operations": ["config:read"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["allowed"]["config:read"])

    def test_nonexistent_namespace_returns_404(self):
        response = _post_can_i(
            self.client,
            {
                "namespace": "does-not-exist",
                "operations": ["config:read"],
                "resource": "app/cfg",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_multiple_operations_batch(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "can-i-*",
                "write": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
            },
        )
        response = _post_can_i(
            self.client,
            {
                "namespace": self.ns.name,
                "operations": ["config:read", "secret:tag", "namespace:write"],
                "resource": "app/cfg",
            },
        )
        self.assertEqual(response.status_code, 200)
        allowed = response.json()["allowed"]
        self.assertEqual(set(allowed), {"config:read", "secret:tag", "namespace:write"})
        self.assertTrue(allowed["config:read"])
        self.assertTrue(allowed["secret:tag"])
        self.assertTrue(allowed["namespace:write"])

    def test_invalid_operation_format_rejected(self):
        response = _post_can_i(
            self.client,
            {
                "operations": ["not-an-operation"],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_empty_operations_rejected(self):
        response = _post_can_i(
            self.client,
            {
                "operations": [],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_unauthenticated_returns_403(self):
        response = _post_can_i(
            self.client,
            {
                "operations": ["global:admin"],
            },
            authenticate=False,
        )
        self.assertEqual(response.status_code, 403)
