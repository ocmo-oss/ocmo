"""Tests for limit/offset pagination on list-style API endpoints."""

import json

from django.test import Client, TestCase

from core.managers.auth import AuthManager
from core.managers.global_permissions import GlobalPermissionsManager
from core.managers.tree import TreeManager
from core.models import GlobalPermissionRule
from core.schemas import GlobalPermissionRulePayload
from core.tests.namespace_helpers import create_test_namespace


class ListPaginationApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("paginate-test")

    def _create_config(self, path: str):
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/{path}",
            data=b"key: value\n",
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def _update_config(self, path: str):
        return self.client.put(
            f"/api/v1/ns/{self.ns.name}/~config/~update/{path}",
            data=b"key: updated\n",
            content_type="application/yaml",
        )

    def test_search_pagination_beyond_fifty_results(self):
        for i in range(55):
            self._create_config(f"pagsearch/cfg-{i:03d}")

        first = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~search/",
            {"q": "pagsearch/cfg", "types": "config", "limit": 20, "offset": 0},
        )
        self.assertEqual(first.status_code, 200, first.content)
        body = first.json()
        self.assertEqual(body["count"], 55)
        self.assertEqual(len(body["items"]), 20)

        second = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~search/",
            {"q": "pagsearch/cfg", "types": "config", "limit": 20, "offset": 50},
        )
        self.assertEqual(second.status_code, 200, second.content)
        body2 = second.json()
        self.assertEqual(body2["count"], 55)
        self.assertEqual(len(body2["items"]), 5)

    def test_navigate_children_pagination(self):
        for i in range(12):
            self._create_config(f"nav-dir/cfg-{i:02d}")

        page1 = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~navigate/nav-dir",
            {"limit": 5, "offset": 0},
        )
        self.assertEqual(page1.status_code, 200, page1.content)
        data = page1.json()
        self.assertEqual(data["children_count"], 12)
        self.assertEqual(len(data["children"]), 5)

        page3 = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~navigate/nav-dir",
            {"limit": 5, "offset": 10},
        )
        self.assertEqual(page3.status_code, 200, page3.content)
        data3 = page3.json()
        self.assertEqual(data3["children_count"], 12)
        self.assertEqual(len(data3["children"]), 2)

    def test_navigate_recursive_children_pagination(self):
        for i in range(8):
            self._create_config(f"rec-root/sub/cfg-{i}")

        response = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~navigate/rec-root",
            {"recursive": "true", "limit": 3, "offset": 2},
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        # 8 configs plus the intermediate folder ``rec-root/sub``.
        self.assertEqual(data["children_count"], 9)
        self.assertEqual(len(data["children"]), 3)

    def test_versions_pagination(self):
        path = "versioned/cfg"
        self._create_config(path)
        for i in range(4):
            update = self.client.put(
                f"/api/v1/ns/{self.ns.name}/~config/~update/{path}",
                data=f"key: value-{i}\n".encode(),
                content_type="application/yaml",
            )
            self.assertEqual(update.status_code, 200, update.content)

        response = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~versions/{path}",
            {"limit": 2, "offset": 1},
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["versions_count"], 5)
        self.assertEqual(len(data["versions"]), 2)
        versions = [row["version"] for row in data["versions"]]
        self.assertEqual(versions, [4, 3])

    def test_set_tag_on_dotted_config_path(self):
        """POST ~tag must not be routed as DELETE ~tag/{path}/{tag} (405 on dotted paths)."""
        path = "app/cfg.yaml"
        self._create_config(path)
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~tag/{path}",
            data=json.dumps({"tag": "release", "version": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_versions_search_by_tag_and_version_number(self):
        path = "versioned/searchable"
        self._create_config(path)
        for i in range(3):
            update = self._update_config(path)
            self.assertEqual(update.status_code, 200, update.content)

        tagged = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~tag/{path}",
            data=json.dumps({"tag": "release", "version": 2}),
            content_type="application/json",
        )
        self.assertEqual(tagged.status_code, 200, tagged.content)

        by_tag = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~versions/{path}",
            {"q": "release"},
        )
        self.assertEqual(by_tag.status_code, 200, by_tag.content)
        self.assertEqual(by_tag.json()["versions_count"], 1)
        self.assertEqual(by_tag.json()["versions"][0]["version"], 2)

        untagged = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~tag/{path}",
            data=json.dumps({"tag": "release", "version": None}),
            content_type="application/json",
        )
        self.assertEqual(untagged.status_code, 200, untagged.content)

        deleted = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~tag/{path}",
            data=json.dumps({"tag": "release", "version": None}),
            content_type="application/json",
        )
        self.assertIn(deleted.status_code, (200, 204))

        by_version = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~versions/{path}",
            {"q": "1"},
        )
        self.assertEqual(by_version.status_code, 200, by_version.content)
        self.assertEqual(
            {row["version"] for row in by_version.json()["versions"]},
            {1},
        )

    def test_versions_tagged_only_filter(self):
        path = "versioned/tagged-only"
        self._create_config(path)
        for _ in range(3):
            update = self._update_config(path)
            self.assertEqual(update.status_code, 200, update.content)

        tagged = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~tag/{path}",
            data=json.dumps({"tag": "pinned", "version": 2}),
            content_type="application/json",
        )
        self.assertEqual(tagged.status_code, 200, tagged.content)

        response = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~versions/{path}",
            {"tagged_only": "true"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["versions_count"], 1)
        self.assertEqual(data["versions"][0]["version"], 2)
        self.assertEqual(data["versions"][0]["tags"], ["pinned"])

    def test_locks_list_pagination(self):
        for name in ("lock-a", "lock-b", "lock-c"):
            self._create_config(f"locks/{name}")
            created = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~lock/locks/{name}",
                data=json.dumps({"reason": f"freeze {name}"}),
                content_type="application/json",
            )
            self.assertEqual(created.status_code, 201, created.content)

        response = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~lock/",
            {"limit": 2, "offset": 1},
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["locks"]), 2)

    def test_global_permissions_list_pagination(self):
        auth = AuthManager(
            {
                "_type": "user",
                "sub": "admin-1",
                "email": "admin@example.com",
                "groups": "ocmo-global-admins",
            }
        )
        mgr = GlobalPermissionsManager(auth=auth)
        payload = GlobalPermissionRulePayload(
            namespace="paginate-*",
            read={"actors": [{"kind": "User", "claims": {"email": "*"}}]},
        )
        for _ in range(3):
            mgr.create(payload)

        response = self.client.get(
            "/api/v1/global-permissions/",
            {"limit": 2, "offset": 1},
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["count"], GlobalPermissionRule.objects.count())
        self.assertEqual(len(data["rules"]), 2)


class SearchManagerPaginationTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("search-mgr-test")
        for i in range(60):
            TreeManager(self.ns, f"pagitems/cfg-{i:03d}", auth=None).create_item("key: x\n", "config")

    def test_search_returns_queryset_without_auth(self):
        qs = TreeManager(self.ns, "", auth=None).search(query="pagitems/cfg", node_types=["config"])
        self.assertEqual(qs.count(), 60)

    def test_search_returns_visible_list_with_auth(self):
        auth = AuthManager(
            {
                "_type": "user",
                "sub": "user-1",
                "email": "admin@example.com",
            }
        )
        results = TreeManager(self.ns, "", auth=auth).search(query="pagitems/cfg", node_types=["config"])
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 60)
