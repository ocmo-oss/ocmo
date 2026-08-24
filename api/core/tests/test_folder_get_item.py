"""GET folder exposes tree metadata (author, created_at)."""

from django.test import Client, TestCase

from core.managers.tree import TreeManager
from core.tests.namespace_helpers import create_test_namespace


class FolderGetItemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("folder-get-test")
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: value\n", "config")

    def test_get_folder_includes_author_and_created_at(self):
        resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~get/app")
        self.assertEqual(resp.status_code, 200, resp.content)
        payload = resp.json()
        self.assertEqual(payload["node_type"], "folder")
        self.assertIn("author", payload)
        self.assertTrue(payload["author"])
        self.assertIn("created_at", payload)
        self.assertTrue(payload["created_at"])
