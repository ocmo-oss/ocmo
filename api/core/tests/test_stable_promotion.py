from django.test import Client, TestCase

from core.exceptions import ReservedTagsCantBeSet
from core.managers.tree import TreeManager
from core.models import Config
from core.schemas.requests import TagPayload
from core.tests.namespace_helpers import create_test_namespace


class StablePromotionApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("stabletest", description="test")
        self._create_config("app/cfg", "key: one\n")
        self._create_config("app/cfg2", "key: two\n")

    def _create_config(self, path: str, body: bytes):
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/{path}",
            data=body,
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def _update_config(self, path: str, body: bytes):
        response = self.client.put(
            f"/api/v1/ns/{self.ns.name}/~config/~update/{path}",
            data=body,
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def _resolve(self, path: str, **params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"/api/v1/ns/{self.ns.name}/~resolve/{path}"
        if query:
            url = f"{url}?{query}"
        return self.client.get(url)

    def _get_config(self, path: str):
        return Config.objects.get(namespace=self.ns, path=path)

    def test_stable_promoted_on_successful_resolve(self):
        response = self._resolve("app/cfg", **{"mark-stable": "true"})
        self.assertEqual(response.status_code, 200, response.content)

        cfg = self._get_config("app/cfg")
        self.assertEqual(cfg.tags.get("stable"), 1)

    def test_stable_not_promoted_by_default(self):
        response = self._resolve("app/cfg")
        self.assertEqual(response.status_code, 200, response.content)

        cfg = self._get_config("app/cfg")
        self.assertNotIn("stable", cfg.tags)

    def test_stable_promotion_is_idempotent(self):
        first = self._resolve("app/cfg", **{"mark-stable": "true"})
        self.assertEqual(first.status_code, 200, first.content)

        second = self._resolve("app/cfg", **{"mark-stable": "true"})
        self.assertEqual(second.status_code, 200, second.content)

        cfg = self._get_config("app/cfg")
        self.assertEqual(cfg.tags.get("stable"), 1)

    def test_trace_only_skips_stable_promotion(self):
        response = self._resolve("app/cfg", **{"mark-stable": "true", "trace_only": "true"})
        self.assertEqual(response.status_code, 200, response.content)

        cfg = self._get_config("app/cfg")
        self.assertNotIn("stable", cfg.tags)

    def test_folder_resolve_promotes_all_configs(self):
        response = self._resolve("app", **{"mark-stable": "true"})
        self.assertEqual(response.status_code, 200, response.content)

        data = response.json()
        self.assertEqual(data["length"], 2)

        self.assertEqual(self._get_config("app/cfg").tags.get("stable"), 1)
        self.assertEqual(self._get_config("app/cfg2").tags.get("stable"), 1)

    def test_folder_partial_failure_leaves_tags_unchanged(self):
        self._update_config("app/cfg2", b"key: v2\n")

        response = self._resolve("app", **{"mark-stable": "true", "version": "2"})
        self.assertEqual(response.status_code, 404, response.content)

        self.assertNotIn("stable", self._get_config("app/cfg").tags)
        self.assertNotIn("stable", self._get_config("app/cfg2").tags)

    def test_stable_advances_to_new_version_after_update(self):
        self._resolve("app/cfg", **{"mark-stable": "true"})
        self._update_config("app/cfg", b"key: updated\n")
        self._resolve("app/cfg", **{"mark-stable": "true"})

        cfg = self._get_config("app/cfg")
        self.assertEqual(cfg.tags.get("stable"), 2)


class StablePromotionManagerTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("stablemgr", description="test")
        TreeManager(self.ns, "cfg", auth=None).create_item("hello: world\n", "config")

    def test_reserved_stable_tag_cannot_be_set_via_tag_api(self):
        tm = TreeManager(self.ns, "cfg", auth=None)
        with self.assertRaises(ReservedTagsCantBeSet):
            tm.set_item_tag(TagPayload(tag="stable", version=1))

    def test_promote_stable_tag_updates_config(self):
        tm = TreeManager(self.ns, "cfg", auth=None)
        changed = tm.promote_stable_tag(1)
        self.assertTrue(changed)

        cfg = Config.objects.get(namespace=self.ns, path="cfg")
        self.assertEqual(cfg.tags["stable"], 1)

    def test_promote_stable_tag_noop_when_unchanged(self):
        tm = TreeManager(self.ns, "cfg", auth=None)
        tm.promote_stable_tag(1)
        changed = tm.promote_stable_tag(1)
        self.assertFalse(changed)
