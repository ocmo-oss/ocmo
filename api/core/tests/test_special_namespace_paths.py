"""Access control for built-in namespace configs and companion secrets."""

from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from core.exceptions import NotFound, PermissionDenied
from core.managers.auth import AuthManager
from core.managers.permissions import PermissionsManager
from core.managers.resolver_tokens import ResolverTokenManager
from core.managers.tree import TreeManager
from core.managers.tree_capabilities import compute_tree_capabilities
from core.models import GlobalPermissionRule, Namespace
from core.utils.namespace_special_configs import init_namespace_special_configs
from core.utils.permissions_compiler import PermissionsCompiler

_SPECIAL_PATHS = (
    "_permissions",
    "_webhooks",
    "_git_sync",
    "_permissions.schema",
    "_webhooks.schema",
    "_git_sync.schema",
    "_webhooks_secret",
    "_git_sync_secret",
)
_SPECIAL_CONFIGS = ("_permissions", "_webhooks", "_git_sync")

_PERMISSIONS = """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "*"
    actions:
      - "*:*"
    resources:
      - "**"
"""

_EXTEND_YAML = """\
_ocmo:
  extend:
    mode: accumulate
    configs:
      - _permissions@latest
key: value
"""

_SECRET_PARAM_YAML = """\
_ocmo:
  parameters:
    hmac_key:
      type: secret
      value: _webhooks_secret@latest
      description: HMAC signing key for webhook payloads
key: "{!hmac_key}"
"""

_WEBHOOKS_WITH_SECRET = """\
_ocmo:
  parameters:
    hmac_key:
      type: secret
      value: _webhooks_secret@latest
      description: HMAC signing key for webhook payloads
webhooks: []
"""


def _grant_namespace_read():
    GlobalPermissionRule.objects.create(
        position=1.0,
        rule={
            "namespace": "special-*",
            "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
        },
    )


def _grant_namespace_write(email: str):
    GlobalPermissionRule.objects.create(
        position=1.0,
        rule={
            "namespace": "special-*",
            "write": {"actors": [{"kind": "User", "claims": {"email": email}}]},
        },
    )


_TEST_MASTER_KEY = "ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs="


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class SpecialNamespacePathsTestCase(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.client = Client()
        self.ns = Namespace.objects.create(name="special-ns-test", description="test")
        init_namespace_special_configs(self.ns)
        TreeManager(self.ns, "_permissions", auth=None).update_item(_PERMISSIONS)
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: value\n", "config")
        TreeManager(self.ns, "app/folder", auth=None).create_item("nested: true\n", "config")

    def tearDown(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def _reader_auth(self) -> AuthManager:
        return AuthManager(
            {
                "_type": "user",
                "email": "reader@example.com",
                "name": "Reader",
            }
        )

    def _writer_auth(self) -> AuthManager:
        return AuthManager(
            {
                "_type": "user",
                "email": "writer@example.com",
                "name": "Writer",
            }
        )

    def _patch_client_auth(self, auth: AuthManager):
        return patch(
            "core.managers.auth.AuthManager.from_request",
            return_value=auth,
        )

    def _create_resolver(self, path: str = "app/svc") -> tuple[str, str]:
        TreeManager(self.ns, path, auth=None).create_item("{}", "resolver")
        resolver = TreeManager(self.ns, path, auth=None).get_or_raise(["resolver"])
        return path, (mgr.plaintext if (mgr := ResolverTokenManager.from_resolver(resolver, 1)) else None)


class VisibilityTests(SpecialNamespacePathsTestCase):
    def test_navigate_root_hides_special_paths_for_read_only_user(self):
        _grant_namespace_read()
        auth = self._reader_auth()
        result = TreeManager(self.ns, "", auth=auth).navigate()
        child_paths = {child["path"] for child in result["children"]}
        for path in _SPECIAL_PATHS:
            self.assertNotIn(path, child_paths)

    def test_navigate_root_shows_special_paths_for_write_user(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        result = TreeManager(self.ns, "", auth=auth).navigate()
        child_paths = {child["path"] for child in result["children"]}
        for path in _SPECIAL_PATHS:
            self.assertIn(path, child_paths)

    def test_search_hides_special_paths_for_read_only_user(self):
        _grant_namespace_read()
        auth = self._reader_auth()
        results = TreeManager(self.ns, "", auth=auth).search(query="_permissions")
        self.assertEqual(results, [])

    def test_direct_navigate_special_path_returns_not_found_for_reader(self):
        _grant_namespace_read()
        auth = self._reader_auth()
        with self.assertRaises(NotFound):
            TreeManager(self.ns, "_permissions", auth=auth).navigate()

    def test_api_navigate_root_hides_special_paths_for_reader(self):
        _grant_namespace_read()
        with self._patch_client_auth(self._reader_auth()):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~navigate/")
        self.assertEqual(resp.status_code, 200, resp.content)
        child_paths = {child["path"] for child in resp.json()["children"]}
        for path in _SPECIAL_PATHS:
            self.assertNotIn(path, child_paths)


class ImmutabilityTests(SpecialNamespacePathsTestCase):
    def test_delete_special_paths_denied_for_writer(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        for path in _SPECIAL_PATHS:
            with self.subTest(path=path):
                with self.assertRaises(PermissionDenied):
                    TreeManager(self.ns, path, auth=auth).delete_item(preview=False)

    def test_delete_version_denied_for_special_configs_and_secrets(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        for path in _SPECIAL_PATHS:
            with self.subTest(path=path):
                with self.assertRaises(PermissionDenied):
                    TreeManager(self.ns, path, auth=auth).delete_item(preview=False, version=1)

    def test_move_special_path_denied(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        with self.assertRaises(PermissionDenied):
            TreeManager(self.ns, "_permissions", auth=auth).move_item("other/_permissions")

    def test_copy_special_path_denied(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        with self.assertRaises(PermissionDenied):
            TreeManager(self.ns, "_permissions", auth=auth).copy_item("copy/_permissions")

    def test_api_delete_special_config_returns_403(self):
        resp = self.client.delete(f"/api/v1/ns/{self.ns.name}/~delete/_permissions")
        self.assertEqual(resp.status_code, 403, resp.content)


class ResolveTests(SpecialNamespacePathsTestCase):
    def test_resolve_special_config_denied_for_reader(self):
        _grant_namespace_read()
        with self._patch_client_auth(self._reader_auth()):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve/_permissions")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolve_special_config_allowed_for_writer(self):
        _grant_namespace_write("writer@example.com")
        with self._patch_client_auth(self._writer_auth()):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve/_permissions")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_resolve_parameters_special_config_denied_for_reader(self):
        _grant_namespace_read()
        with self._patch_client_auth(self._reader_auth()):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve-parameters/_permissions")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_resolver_cannot_resolve_special_config(self):
        path, _token = self._create_resolver()
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": path.split("/")[-1],
                "access_scope": "/".join(path.split("/")[:-1]),
                "token_number": 1,
            }
        )
        self.assertFalse(TreeManager(self.ns, "_permissions", auth=auth).is_resolvable)

    def test_folder_resolve_skips_special_configs(self):
        _grant_namespace_write("writer@example.com")
        with self._patch_client_auth(self._writer_auth()):
            resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve/app")
        self.assertEqual(resp.status_code, 200, resp.content)
        names = {item["name"] for item in resp.json()["items"]}
        for special in _SPECIAL_CONFIGS:
            self.assertNotIn(special, names)
            self.assertNotIn(special.split("/")[-1], names)

    def test_include_cannot_override_special_folder_resolve_exclusion(self):
        from core.managers.resolution import ResolutionManager
        from core.models import Config

        auth = self._writer_auth()
        _grant_namespace_write("writer@example.com")
        mgr = ResolutionManager(
            self.ns,
            "app",
            auth=auth,
            query_params={},
            base_url="http://testserver/",
        )
        mgr.resolver_config = {"include": ["**", "_permissions"]}
        configs = list(
            Config.objects.filter(
                namespace=self.ns,
                path__in=["_permissions", "app/cfg", "app/folder"],
            )
        )
        configs = [cfg for cfg in configs if TreeManager.for_item(self.ns, cfg, auth=auth).is_folder_resolvable]
        filtered = mgr._filter_configs(configs)
        filtered_paths = {cfg.path for cfg in filtered}
        self.assertNotIn("_permissions", filtered_paths)
        self.assertIn("app/cfg", filtered_paths)


class ExtendAndSecretParamTests(SpecialNamespacePathsTestCase):
    def test_config_update_with_extend_to_special_config_denied(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        with self.assertRaises(PermissionDenied):
            TreeManager(self.ns, "app/cfg", auth=auth).update_item(_EXTEND_YAML)

    def test_config_update_with_forbidden_secret_param_denied(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        with self.assertRaises(PermissionDenied):
            TreeManager(self.ns, "app/cfg", auth=auth).update_item(_SECRET_PARAM_YAML)

    def test_webhooks_config_may_reference_companion_secret(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        item = TreeManager(self.ns, "_webhooks", auth=auth).update_item(_WEBHOOKS_WITH_SECRET)
        self.assertEqual(item.path, "_webhooks")

    def test_resolve_config_with_extend_to_special_config_denied(self):
        from core.managers.resolving import ResolvePipelineManager

        TreeManager(self.ns, "app/bad", auth=None).create_item("key: value\n", "config")
        from core.models import ConfigVersion

        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/bad", version=1).update(
            data=_EXTEND_YAML
        )

        with self.assertRaises(PermissionDenied):
            ResolvePipelineManager(
                self.ns,
                "app/bad",
                "latest",
                auth=self._writer_auth(),
            ).resolve()


class TreeCapabilitiesUnitTests(SpecialNamespacePathsTestCase):
    def test_ordinary_path_all_capabilities_true(self):
        _grant_namespace_read()
        caps = compute_tree_capabilities(
            self.ns,
            "app/cfg",
            self._reader_auth(),
        )
        self.assertTrue(caps.is_visible)
        self.assertTrue(caps.is_deletable)
        self.assertTrue(caps.is_extend_target)

    def test_auth_none_all_capabilities_true(self):
        caps = compute_tree_capabilities(self.ns, "_permissions", None)
        self.assertTrue(caps.is_resolvable)
        self.assertTrue(caps.is_deletable)

    def test_builtin_config_reader_cannot_resolve_or_extend(self):
        _grant_namespace_read()
        auth = self._reader_auth()
        caps = compute_tree_capabilities(self.ns, "_permissions", auth)
        self.assertFalse(caps.is_visible)
        self.assertFalse(caps.is_resolvable)
        self.assertFalse(caps.is_extend_target)
        self.assertFalse(caps.is_deletable)

    def test_builtin_config_writer_can_resolve_not_extend(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        caps = compute_tree_capabilities(self.ns, "_webhooks", auth)
        self.assertTrue(caps.is_visible)
        self.assertTrue(caps.is_resolvable)
        self.assertFalse(caps.is_extend_target)
        self.assertFalse(caps.is_folder_resolvable)

    def test_builtin_config_resolver_cannot_resolve_even_with_write(self):
        _grant_namespace_write("writer@example.com")
        path, _token = self._create_resolver()
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": path.split("/")[-1],
                "access_scope": "/".join(path.split("/")[:-1]),
                "token_number": 1,
            }
        )
        caps = compute_tree_capabilities(self.ns, "_permissions", auth)
        self.assertFalse(caps.is_resolvable)

    def test_companion_secret_param_only_from_parent_config(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        ok = compute_tree_capabilities(
            self.ns,
            "_webhooks_secret",
            auth,
            referencing_config_path="_webhooks",
        )
        self.assertTrue(ok.is_available_for_param)
        bad = compute_tree_capabilities(
            self.ns,
            "_webhooks_secret",
            auth,
            referencing_config_path="app/cfg",
        )
        self.assertFalse(bad.is_available_for_param)


class PermissionsUnitTests(SpecialNamespacePathsTestCase):
    def test_resolver_cannot_resolve_special_path_even_in_scope(self):
        _grant_namespace_read()
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": "svc",
                "access_scope": "",
                "token_number": 1,
            }
        )
        pm = PermissionsManager(auth, self.ns)
        self.assertFalse(pm.check_tree("config:resolve", "_permissions"))

    def test_writer_can_read_special_path(self):
        _grant_namespace_write("writer@example.com")
        auth = self._writer_auth()
        pm = PermissionsManager(auth, self.ns)
        self.assertTrue(pm.check_tree("config:read", "_permissions"))
