"""Resolve endpoint permission enforcement tests."""

from unittest.mock import patch

from django.core.cache import cache, caches
from django.test import Client, TestCase, override_settings

from core.managers.auth import AuthManager
from core.managers.resolver_tokens import ResolverTokenManager
from core.managers.tree import TreeManager
from core.models import ConfigVersion, GlobalPermissionRule, Namespace
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
      - kind: Resolver
        path: app/svc
    actions:
      - config:resolve
      - secret:resolve
    resources:
      - shared/**
      - other/**
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

_EXTEND_SHARED_YAML = """\
_ocmo:
  extend:
    mode: accumulate
    configs:
      - ../../shared/base@latest
key: child
"""

_RENDER_SHARED_YAML = """\
_ocmo:
  render:
    mode: distribute
    templates:
      - ../../shared/tmpl@latest
key: child
"""

_SECRET_PARAM_YAML = """\
_ocmo:
  parameters:
    cred:
      type: secret
      value: ../../shared/secret@latest
      description: Shared secret reference for resolve tests
key: "{!cred}"
"""

_SECRET_PARAM_B64_YAML = """\
_ocmo:
  parameters:
    cred:
      type: secret
      value: ../../shared/secret@latest
      description: Shared secret reference for resolve tests
      transformers:
        - b64_encode
key: "{!cred}"
"""

_MISSING_SECRET_PARAM_YAML = """\
_ocmo:
  parameters:
    cred:
      type: secret
      value: shared/missing-secret@latest
      description: Reference to a secret that does not exist
key: "{!cred}"
"""


from core.utils.namespace_special_configs import init_namespace_special_configs


def _init_special_configs(ns: Namespace) -> None:
    init_namespace_special_configs(ns)


def _grant_test_users_global_access() -> None:
    GlobalPermissionRule.objects.create(
        position=1.0,
        rule={
            "namespace": "resolve-perm-*",
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


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ResolvePermissionsTestCase(TestCase):
    def setUp(self):
        cache.clear()
        caches["resolve"].clear()
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.client = Client()
        self.ns = Namespace.objects.create(name="resolve-perm-ns", description="test")
        _init_special_configs(self.ns)
        _grant_test_users_global_access()
        TreeManager(self.ns, "_permissions", auth=None).update_item(_POLICIES)

        TreeManager(self.ns, "app/cfg", auth=None).create_item(_BASE_YAML, "config")
        TreeManager(self.ns, "other/cfg", auth=None).create_item(_BASE_YAML, "config")
        TreeManager(self.ns, "shared/base", auth=None).create_item("base: true\n", "config")
        TreeManager(self.ns, "shared/tmpl", auth=None).create_item("x: {{ key }}\n", "template")
        with self._patch_client_auth(self._user_auth("writer@example.com")):
            secret_resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~secret/~create/shared/secret",
                data="token: abc\n",
                content_type="application/yaml",
            )
        self.assertEqual(secret_resp.status_code, 201, secret_resp.content)

        self.resolver_path, self.resolver_token = self._create_resolver("app/svc")

    def tearDown(self):
        cache.clear()
        caches["resolve"].clear()
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def _user_auth(self, email: str) -> AuthManager:
        return AuthManager({"_type": "user", "email": email, "name": email.split("@")[0]})

    def _resolver_auth(self) -> AuthManager:
        scope = "/".join(self.resolver_path.split("/")[:-1])
        name = self.resolver_path.split("/")[-1]
        return AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": name,
                "access_scope": scope,
                "token_number": 1,
            }
        )

    def _patch_client_auth(self, auth: AuthManager):
        return patch(
            "core.managers.auth.AuthManager.from_request",
            return_value=auth,
        )

    def _create_resolver(self, path: str) -> tuple[str, str]:
        TreeManager(self.ns, path, auth=None).create_item("{}", "resolver")
        resolver = TreeManager(self.ns, path, auth=None).get_or_raise(["resolver"])
        return path, (mgr.plaintext if (mgr := ResolverTokenManager.from_resolver(resolver, 1)) else None)

    def _resolve(self, path: str, **params):
        query = "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
        url = f"/api/v1/ns/{self.ns.name}/~resolve/{path}"
        if query:
            url = f"{url}?{query}"
        return self.client.get(url)

    def _download_first_item(self, resp, auth: AuthManager | None = None) -> bytes:
        self.assertEqual(resp.status_code, 200, resp.content)
        item_url = resp.json()["items"][0]["url"]
        # URL may be absolute; Client accepts path-only when same host.
        path = item_url.split("/api/v1/", 1)[-1]
        path = "/api/v1/" + path
        if auth is not None:
            with self._patch_client_auth(auth):
                dl = self.client.get(path)
        else:
            dl = self.client.get(path)
        self.assertEqual(dl.status_code, 200, dl.content)
        return dl.content

    def test_read_only_user_denied_on_resolve(self):
        with self._patch_client_auth(self._user_auth("reader@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolve_user_can_resolve_without_read_permissions(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_resolve_only_user_denied_on_get_without_read(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~get/app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolve_denied_when_extend_base_not_permitted(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_EXTEND_SHARED_YAML
        )
        with self._patch_client_auth(self._user_auth("reader@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolve_denied_when_render_template_not_permitted(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_RENDER_SHARED_YAML
        )
        with self._patch_client_auth(self._user_auth("reader@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolve_parameters_with_secret_param_resolves_relative_reference(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_SECRET_PARAM_YAML
        )
        with self._patch_client_auth(self._user_auth("writer@example.com")):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve-parameters/app/cfg")
        self.assertEqual(resp.status_code, 200, resp.content)
        cred = resp.json()["parameters"]["cred"]
        self.assertEqual(cred["type"], "secret")
        self.assertEqual(cred["secret_reference"], "../../shared/secret@latest")
        self.assertEqual(cred["effective_value"], "***")

    def test_resolve_denied_when_secret_param_not_permitted(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_SECRET_PARAM_YAML
        )
        with self._patch_client_auth(self._user_auth("reader@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolve_missing_secret_param_returns_422(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_MISSING_SECRET_PARAM_YAML
        )
        with self._patch_client_auth(self._user_auth("writer@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 422, resp.content)
        self.assertIn("Secret", resp.json()["error"])

    def test_resolve_no_creds_bypasses_secret_resolve(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_SECRET_PARAM_YAML
        )
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            self._user_auth("resolver-user@example.com")
            resp = self._resolve("app/cfg", **{"no-creds": "true"})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = self._download_first_item(resp)
        self.assertIn(b"<secret-value-placeholder>", body)
        self.assertNotIn(b"abc", body)

    def test_resolve_no_creds_skips_secret_transformers(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_SECRET_PARAM_B64_YAML
        )
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve("app/cfg", **{"no-creds": "true"})
        body = self._download_first_item(resp)
        self.assertIn(b"<secret-value-placeholder>", body)
        self.assertNotIn(b"YWJj", body)  # base64("abc")

    def test_resolve_no_creds_false_still_requires_secret_resolve(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_SECRET_PARAM_YAML
        )
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolver_in_scope_direct_resolve(self):
        with self._patch_client_auth(self._resolver_auth()):
            resp = self._resolve("cfg")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_resolver_can_download_resolved_artifact(self):
        with self._patch_client_auth(self._resolver_auth()):
            resp = self._resolve("cfg")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = self._download_first_item(resp)
        self.assertGreater(len(body), 0)

    def test_download_ignores_request_auth(self):
        """Signed download URL works without Authorization (token is the credential)."""
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = self._download_first_item(resp)
        self.assertGreater(len(body), 0)

    def test_resolver_scope_root_dot_path(self):
        with self._patch_client_auth(self._resolver_auth()):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve/@")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_resolver_direct_resolve_outside_scope_denied_despite_policy(self):
        """Policy grant on other/cfg does not allow direct resolve outside scope."""
        with self._patch_client_auth(self._resolver_auth()):
            resp = self._resolve("../other/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolver_extends_out_of_scope_base_with_policy_grant(self):
        TreeManager(self.ns, "app/child", auth=None).create_item(_EXTEND_SHARED_YAML, "config")
        with self._patch_client_auth(self._resolver_auth()):
            resp = self._resolve("child")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_resolver_secret_param_out_of_scope_with_policy_grant(self):
        TreeManager(self.ns, "app/secret-cfg", auth=None).create_item(_SECRET_PARAM_YAML, "config")
        with self._patch_client_auth(self._resolver_auth()):
            resp = self._resolve("secret-cfg")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_mark_stable_requires_config_write(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve("app/cfg", **{"mark-stable": "true"})
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolve_parameters_requires_config_resolve(self):
        with self._patch_client_auth(self._user_auth("reader@example.com")):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve-parameters/app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolve_parameters_works_without_read_permissions(self):
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve-parameters/app/cfg")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_cache_hit_still_enforces_config_resolve(self):
        writer = self._user_auth("writer@example.com")
        with self._patch_client_auth(writer):
            first = self._resolve("app/cfg")
        self.assertEqual(first.status_code, 200, first.content)

        TreeManager(self.ns, "_permissions", auth=None).update_item(
            """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "writer@example.com"
    actions:
      - config:read
    resources:
      - "**"
"""
        )
        PermissionsCompiler._policy_cache.clear()
        writer_fresh = self._user_auth("writer@example.com")
        with self._patch_client_auth(writer_fresh):
            second = self._resolve("app/cfg")
        self.assertEqual(second.status_code, 403, second.content)

    def _warm_resolve_cache(self, path: str, **params):
        writer = self._user_auth("writer@example.com")
        with self._patch_client_auth(writer):
            first = self._resolve(path, **params)
        self.assertEqual(first.status_code, 200, first.content)
        with self._patch_client_auth(writer):
            second = self._resolve(path, **params)
        self.assertEqual(second.status_code, 200, second.content)

    def _revoke_to_read_only(self):
        TreeManager(self.ns, "_permissions", auth=None).update_item(
            """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "writer@example.com"
    actions:
      - config:read
    resources:
      - "**"
"""
        )
        PermissionsCompiler._policy_cache.clear()

    def _restrict_resolve_to_app_only(self):
        TreeManager(self.ns, "_permissions", auth=None).update_item(
            """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "writer@example.com"
    actions:
      - config:resolve
    resources:
      - app/**
"""
        )
        PermissionsCompiler._policy_cache.clear()

    def test_cache_hit_denies_when_extend_base_permission_revoked(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_EXTEND_SHARED_YAML
        )
        self._warm_resolve_cache("app/cfg")
        self._restrict_resolve_to_app_only()
        with self._patch_client_auth(self._user_auth("writer@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_cache_hit_denies_when_render_template_permission_revoked(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_RENDER_SHARED_YAML
        )
        self._warm_resolve_cache("app/cfg")
        self._restrict_resolve_to_app_only()
        with self._patch_client_auth(self._user_auth("writer@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_cache_hit_denies_when_secret_param_permission_revoked(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_SECRET_PARAM_YAML
        )
        self._warm_resolve_cache("app/cfg")
        TreeManager(self.ns, "_permissions", auth=None).update_item(
            """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "writer@example.com"
    actions:
      - config:resolve
    resources:
      - "**"
"""
        )
        PermissionsCompiler._policy_cache.clear()
        with self._patch_client_auth(self._user_auth("writer@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_cache_hit_no_creds_skips_secret_permission_on_hit(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_SECRET_PARAM_YAML
        )
        self._warm_resolve_cache("app/cfg", **{"no-creds": "true"})
        TreeManager(self.ns, "_permissions", auth=None).update_item(
            """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "writer@example.com"
    actions:
      - config:resolve
    resources:
      - "**"
"""
        )
        PermissionsCompiler._policy_cache.clear()
        with self._patch_client_auth(self._user_auth("writer@example.com")):
            resp = self._resolve("app/cfg", **{"no-creds": "true"})
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_cache_hit_denied_for_user_without_nested_resolve(self):
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/cfg", version=1).update(
            data=_EXTEND_SHARED_YAML
        )
        self._warm_resolve_cache("app/cfg")
        with self._patch_client_auth(self._user_auth("resolver-user@example.com")):
            resp = self._resolve("app/cfg")
        self.assertEqual(resp.status_code, 403, resp.content)
