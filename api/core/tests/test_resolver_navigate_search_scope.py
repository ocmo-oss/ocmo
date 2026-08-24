"""Resolver access_scope limits for navigate() and search()."""

from django.test import TestCase

from core.exceptions import NotFound
from core.managers.auth import AuthManager
from core.managers.tree import TreeManager
from core.managers.tree_capabilities import compute_tree_capabilities
from core.tests.namespace_helpers import create_test_namespace
from core.utils.permissions_compiler import PermissionsCompiler

_SCOPE = "proj/env/app"
_RESOLVER_PATH = f"{_SCOPE}/svc"


class ResolverNavigateSearchScopeTestCase(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        self.ns = create_test_namespace("resolver-scope-ns")
        TreeManager(self.ns, "other/cfg", auth=None).create_item("key: other\n", "config")
        TreeManager(self.ns, f"{_SCOPE}/cfg", auth=None).create_item("key: in-scope\n", "config")
        TreeManager(self.ns, _RESOLVER_PATH, auth=None).create_item("{}", "resolver")

    def tearDown(self):
        PermissionsCompiler._policy_cache.clear()

    def _resolver_auth(self) -> AuthManager:
        return AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": "svc",
                "access_scope": _SCOPE,
                "token_number": 1,
            }
        )

    def test_capabilities_in_scope_visible(self):
        auth = self._resolver_auth()
        caps = compute_tree_capabilities(self.ns, f"{_SCOPE}/cfg", auth)
        self.assertTrue(caps.is_visible)
        self.assertTrue(caps.is_direct_resolve_target)

    def test_capabilities_out_of_scope_not_visible(self):
        auth = self._resolver_auth()
        caps = compute_tree_capabilities(self.ns, "other/cfg", auth)
        self.assertFalse(caps.is_visible)
        self.assertFalse(caps.is_direct_resolve_target)

    def test_capabilities_scope_root_visible(self):
        auth = self._resolver_auth()
        caps = compute_tree_capabilities(self.ns, _SCOPE, auth)
        self.assertTrue(caps.is_visible)
        self.assertTrue(caps.is_direct_resolve_target)

    def test_capabilities_ancestor_path_not_visible(self):
        auth = self._resolver_auth()
        caps = compute_tree_capabilities(self.ns, "proj", auth)
        self.assertFalse(caps.is_visible)

    def test_navigate_root_excludes_out_of_scope(self):
        auth = self._resolver_auth()
        result = TreeManager(self.ns, "", auth=auth).navigate()
        child_paths = {child["path"] for child in result["children"]}
        self.assertNotIn("other", child_paths)
        self.assertNotIn("other/cfg", child_paths)

    def test_navigate_scope_root_shows_in_scope_children(self):
        auth = self._resolver_auth()
        result = TreeManager(self.ns, _SCOPE, auth=auth).navigate()
        child_paths = {child["path"] for child in result["children"]}
        self.assertIn(f"{_SCOPE}/cfg", child_paths)
        self.assertIn(_RESOLVER_PATH, child_paths)
        self.assertNotIn("other/cfg", child_paths)

    def test_navigate_out_of_scope_raises_not_found(self):
        auth = self._resolver_auth()
        with self.assertRaises(NotFound):
            TreeManager(self.ns, "other", auth=auth).navigate()

    def test_navigate_recursive_only_in_scope(self):
        auth = self._resolver_auth()
        result = TreeManager(self.ns, _SCOPE, auth=auth).navigate(recursive=True)
        child_paths = {child["path"] for child in result["children"]}
        self.assertIn(f"{_SCOPE}/cfg", child_paths)
        self.assertNotIn("other/cfg", child_paths)

    def test_search_from_root_only_in_scope(self):
        auth = self._resolver_auth()
        results = TreeManager(self.ns, "", auth=auth).search(query="cfg")
        result_paths = {item["path"] for item in results}
        self.assertIn(f"{_SCOPE}/cfg", result_paths)
        self.assertNotIn("other/cfg", result_paths)

    def test_search_under_out_of_scope_raises_not_found(self):
        auth = self._resolver_auth()
        with self.assertRaises(NotFound):
            TreeManager(self.ns, "other", auth=auth).search(query="cfg")
