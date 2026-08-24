"""Draft resolve endpoint tests."""

from unittest.mock import patch

from django.core.cache import cache, caches
from django.test import Client, TestCase, override_settings

from core.managers.auth import AuthManager
from core.managers.tree import TreeManager
from core.models import AuditEvent, GlobalPermissionRule, Namespace
from core.utils.permissions_compiler import PermissionsCompiler

_TEST_MASTER_KEY = "ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs="

_POLICIES = """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "reader@example.com"
    actions:
      - config:read
    resources:
      - "**"
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "resolver-user@example.com"
    actions:
      - config:resolve
    resources:
      - app/**
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "writer@example.com"
    actions:
      - "*:*"
    resources:
      - "**"
"""

_BASE_YAML = "key: value\n"

_EXTEND_DRAFT_YAML = """\
_ocmo:
  extend:
    mode: accumulate
    configs:
      - ./shared/base@latest
draft: true
"""


def _grant_test_users_global_access() -> None:
    GlobalPermissionRule.objects.create(
        position=1.0,
        rule={
            "namespace": "resolve-draft-*",
            "read": {
                "actors": [
                    {"kind": "User", "claims": {"email": "reader@example.com"}},
                    {"kind": "User", "claims": {"email": "resolver-user@example.com"}},
                    {"kind": "User", "claims": {"email": "writer@example.com"}},
                ]
            },
            "write": {
                "actors": [
                    {"kind": "User", "claims": {"email": "writer@example.com"}},
                ]
            },
        },
    )


from core.utils.namespace_special_configs import init_namespace_special_configs


def _init_special_configs(ns: Namespace) -> None:
    init_namespace_special_configs(ns)


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ResolveDraftTestCase(TestCase):
    def setUp(self):
        cache.clear()
        caches["resolve"].clear()
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.client = Client()
        self.ns = Namespace.objects.create(name="resolve-draft-ns", description="test")
        _init_special_configs(self.ns)
        _grant_test_users_global_access()
        TreeManager(self.ns, "_permissions", auth=None).update_item(_POLICIES)
        TreeManager(self.ns, "app/cfg", auth=None).create_item(_BASE_YAML, "config")
        TreeManager(self.ns, "app/shared/base", auth=None).create_item("base: true\n", "config")

    def tearDown(self):
        cache.clear()
        caches["resolve"].clear()
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def _user_auth(self, email: str) -> AuthManager:
        return AuthManager({"_type": "user", "email": email, "name": email.split("@")[0]})

    def _patch_client_auth(self, auth: AuthManager):
        return patch(
            "core.managers.auth.AuthManager.from_request",
            return_value=auth,
        )

    def _resolve_draft(self, path: str, body: str, **params):
        query = "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
        url = f"/api/v1/ns/{self.ns.name}/~resolve-draft/{path}"
        if query:
            url = f"{url}?{query}"
        return self.client.post(url, data=body, content_type="application/yaml")

    def test_draft_resolve_existing_path(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve_draft("app/cfg", "key: draft\n")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data["length"], 1)
        self.assertEqual(data["items"][0]["version"], 0)
        self.assertIsNotNone(data["items"][0]["url"])
        self.assertIsNotNone(data["items"][0]["checksum"])

    def test_draft_resolve_new_path(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve_draft("app/new-cfg", "key: new\n")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["items"][0]["version"], 0)

    def test_draft_resolve_extend_chain(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve_draft("app/child", _EXTEND_DRAFT_YAML)
        self.assertEqual(resp.status_code, 200, resp.content)
        item_url = resp.json()["items"][0]["url"]
        path = "/api/v1/" + item_url.split("/api/v1/", 1)[-1]
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            dl = self.client.get(path)
        self.assertEqual(dl.status_code, 200, dl.content)
        self.assertIn(b"base: true", dl.content)
        self.assertIn(b"draft: true", dl.content)

    def test_draft_resolve_denied_without_resolve_permission(self):
        with self._patch_client_auth(self._user_auth("reader@example.com")):
            resp = self._resolve_draft("app/cfg", "key: draft\n")
        self.assertEqual(resp.status_code, 403, resp.content)

    @override_settings(OCMO_AUDIT_MODE="resolve")
    def test_draft_resolve_writes_resolve_request_audit(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve_draft("app/cfg", "key: draft\n")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(
            AuditEvent.objects.filter(
                object_id="app/cfg",
                event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST,
            ).exists()
        )

    def test_draft_resolve_trace_only(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve_draft("app/child", _EXTEND_DRAFT_YAML, **{"trace_only": "true"})
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertTrue(data["trace_only"])
        self.assertEqual(data["root"]["version"], 0)
        self.assertEqual(data["root"]["requested_version"], "draft")
        self.assertIsNone(data["items"][0]["url"])
