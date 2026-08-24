from django.test import Client, TestCase

from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace
from core.utils.permissions_compiler import PermissionsCompiler


class FolderResolveMissingTagsApiTests(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        self.client = Client()
        self.ns = create_test_namespace("missingtagstest", description="test")
        self._create_config("app/cfg", b"key: one\n")
        self._create_config("app/cfg2", b"key: two\n")
        TreeManager(self.ns, "app/cfg", auth=None).promote_stable_tag(1)

    def _create_config(self, path: str, body: bytes):
        TreeManager(self.ns, path, auth=None).create_item(body.decode(), "config")

    def _resolve(self, path: str, **params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"/api/v1/ns/{self.ns.name}/~resolve/{path}"
        if query:
            url = f"{url}?{query}"
        return self.client.get(url)

    def test_folder_resolve_fails_when_any_config_lacks_version(self):
        response = self._resolve("app", version="stable")
        self.assertEqual(response.status_code, 404, response.content)

    def test_folder_resolve_skips_configs_with_missing_version(self):
        response = self._resolve(
            "app",
            version="stable",
            **{"ignore-configs-with-missing-tags": "true"},
        )
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()
        self.assertEqual(data["length"], 1)
        self.assertEqual(data["items"][0]["name"], "cfg")

    def test_folder_resolve_returns_empty_when_all_configs_skipped(self):
        response = self._resolve(
            "app",
            version="release",
            **{"ignore-configs-with-missing-tags": "true"},
        )
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()
        self.assertEqual(data["length"], 0)
        self.assertEqual(data["items"], [])

    def test_single_config_resolve_ignores_skip_flag(self):
        response = self._resolve(
            "app/cfg2",
            version="stable",
            **{"ignore-configs-with-missing-tags": "true"},
        )
        self.assertEqual(response.status_code, 404, response.content)

    def test_resolve_deleted_version_returns_not_found(self):
        TreeManager(self.ns, "app/cfg", auth=None).update_item("key: updated\n")
        TreeManager(self.ns, "app/cfg", auth=None).delete_item(preview=False, version=2)

        response = self._resolve("app/cfg", version="2")
        self.assertEqual(response.status_code, 404, response.content)
        self.assertIn("not found on app/cfg", response.json()["error"])

        missing = self._resolve("app/cfg", version="99")
        self.assertEqual(missing.status_code, 404, missing.content)
        self.assertIn("not found on app/cfg", missing.json()["error"])
