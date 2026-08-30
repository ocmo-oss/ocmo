"""Resolve response includes effective resolver configuration for resolver auth."""

from unittest.mock import patch

from django.core.cache import cache, caches
from django.test import Client, TestCase, override_settings

from core.managers.auth import AuthManager
from core.managers.resolution import ResolutionManager
from core.managers.tree import TreeManager
from core.models import GlobalPermissionRule
from core.tests.namespace_helpers import create_test_namespace
from core.tests.test_resolve_permissions import _TEST_MASTER_KEY
from core.utils.permissions_compiler import PermissionsCompiler


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ResolveResolverResponseTests(TestCase):
    def setUp(self):
        cache.clear()
        caches["resolve"].clear()
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.client = Client()
        self.ns = create_test_namespace("resolve-resolver-response-ns", description="test")
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "*",
                "read": {
                    "actors": [
                        {"kind": "User", "claims": {"email": "writer@example.com"}},
                    ]
                },
            },
        )
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: value\n", "config")
        TreeManager(self.ns, "app/svc", auth=None).create_item(
            'validate: "ls -la {!conf}"\npost_resolve: "ls -la"\n',
            "resolver",
        )
        TreeManager(self.ns, "app/cast-svc", auth=None).create_item(
            "cast:\n"
            "  format: yaml\n"
            "  options:\n"
            "    explicit_start: true\n"
            "    trailing_newline: true\n"
            'validate: "ls -la {!conf}"\n',
            "resolver",
        )
        self.resolver_path = "app/svc"

    def tearDown(self):
        cache.clear()
        caches["resolve"].clear()
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def _resolver_auth(self) -> AuthManager:
        return AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": "svc",
                "access_scope": "app",
                "token_number": 1,
            }
        )

    def _patch_client_auth(self, auth: AuthManager):
        return patch(
            "core.managers.auth.AuthManager.from_request",
            return_value=auth,
        )

    def test_resolver_auth_response_includes_hooks(self):
        with self._patch_client_auth(self._resolver_auth()):
            resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~resolve/cfg",
                HTTP_X_OCMO_RESOLVER_TOKEN="unused-in-patched-test",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        payload = resp.json()
        self.assertIn("resolver", payload)
        hooks = payload["resolver"]["hooks"]
        self.assertEqual(hooks["validate"], "ls -la {!conf}")
        self.assertEqual(hooks["post_resolve"], "ls -la")

    def test_user_auth_response_omits_resolver(self):
        with self._patch_client_auth(
            AuthManager(
                {
                    "_type": "user",
                    "email": "writer@example.com",
                    "name": "writer",
                }
            )
        ):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve/app/cfg")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIsNone(resp.json().get("resolver"))

    def test_effective_resolver_payload_normalizes_hooks(self):
        auth = self._resolver_auth()
        mgr = ResolutionManager(
            self.ns,
            "cfg",
            auth=auth,
            query_params={},
            base_url="http://testserver/",
        )
        payload = mgr._effective_resolver_payload()
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["hooks"]["validate"], "ls -la {!conf}")
        self.assertEqual(payload["hooks"]["post_resolve"], "ls -la")

    def test_resolver_cast_options_merged_on_init(self):
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": "cast-svc",
                "access_scope": "app",
                "token_number": 1,
            }
        )
        mgr = ResolutionManager(
            self.ns,
            "cfg",
            auth=auth,
            query_params={},
            base_url="http://testserver/",
            trace_only=True,
        )
        self.assertEqual(mgr.cast, "yaml")
        self.assertEqual(
            mgr.cast_options,
            {"explicit_start": True, "trailing_newline": True},
        )

    def test_resolver_cast_trace_only_resolve(self):
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": "cast-svc",
                "access_scope": "app",
                "token_number": 1,
            }
        )
        with self._patch_client_auth(auth):
            resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~resolve/cfg",
                {"trace_only": "true"},
                HTTP_X_OCMO_RESOLVER_TOKEN="unused-in-patched-test",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        payload = resp.json()
        self.assertTrue(payload.get("trace_only"))
        self.assertIn("resolver", payload)
