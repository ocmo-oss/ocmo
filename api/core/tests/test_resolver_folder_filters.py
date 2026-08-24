"""Resolver include/exclude glob filters during folder resolve."""

from django.test import TestCase

from core.managers.auth import AuthManager
from core.managers.resolution import ResolutionManager
from core.managers.tree import TreeManager
from core.models import Config
from core.shortcuts import (
    config_path_relative_to_folder,
    match_resolver_glob,
    normalize_resolver_glob_pattern,
)
from core.tests.namespace_helpers import create_test_namespace
from core.utils.permissions_compiler import PermissionsCompiler

_SCOPE = "audit-test"
_RESOLVER_PATH = f"{_SCOPE}/svc"


class ResolverGlobMatchingTests(TestCase):
    def test_normalize_strips_dot_slash_prefix(self):
        self.assertEqual(normalize_resolver_glob_pattern("./new.conf"), "new.conf")

    def test_match_relative_exclude_pattern(self):
        self.assertTrue(match_resolver_glob("./new.conf", "new.conf"))
        self.assertFalse(match_resolver_glob("./new.conf", "other.conf"))

    def test_double_star_matches_nested_paths(self):
        self.assertTrue(match_resolver_glob("**/draft/**", "team/draft/cfg"))
        self.assertFalse(match_resolver_glob("**/draft/**", "team/prod/cfg"))


class ResolverFolderExcludeTests(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        self.ns = create_test_namespace("resolver-exclude-ns")
        TreeManager(self.ns, f"{_SCOPE}/keep.conf", auth=None).create_item("keep: yes\n", "config")
        TreeManager(self.ns, f"{_SCOPE}/new.conf", auth=None).create_item("new: yes\n", "config")
        TreeManager(self.ns, f"{_SCOPE}/nested/draft/cfg", auth=None).create_item("draft: yes\n", "config")
        TreeManager(self.ns, _RESOLVER_PATH, auth=None).create_item(
            "exclude:\n  - ./new.conf\n  - '**/draft/**'\n",
            "resolver",
        )

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

    def _filter_paths(self, exclude: list[str] | None = None) -> set[str]:
        auth = self._resolver_auth()
        mgr = ResolutionManager(
            self.ns,
            ".",
            auth=auth,
            query_params={},
            base_url="http://testserver/",
        )
        if exclude is not None:
            mgr.resolver_config = {"exclude": exclude}
        configs = list(
            Config.objects.filter(
                namespace=self.ns,
                path__startswith=f"{_SCOPE}/",
            )
        )
        return {cfg.path for cfg in mgr._filter_configs(configs)}

    def test_filter_configs_uses_folder_relative_paths(self):
        paths = self._filter_paths(exclude=["./new.conf"])
        self.assertIn(f"{_SCOPE}/keep.conf", paths)
        self.assertNotIn(f"{_SCOPE}/new.conf", paths)
        self.assertIn(f"{_SCOPE}/nested/draft/cfg", paths)

    def test_filter_configs_supports_double_star_patterns(self):
        paths = self._filter_paths(exclude=["**/draft/**"])
        self.assertIn(f"{_SCOPE}/keep.conf", paths)
        self.assertIn(f"{_SCOPE}/new.conf", paths)
        self.assertNotIn(f"{_SCOPE}/nested/draft/cfg", paths)

    def test_config_path_relative_to_folder(self):
        self.assertEqual(
            config_path_relative_to_folder(f"{_SCOPE}/new.conf", _SCOPE),
            "new.conf",
        )
