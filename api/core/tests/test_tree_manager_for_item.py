import json

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from core.managers.tree import TreeManager
from core.models import Config, TreeItem
from core.tests.namespace_helpers import create_test_namespace


class TreeManagerForItemTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("for-item-test", description="test")
        TreeManager(self.ns, "app/cfg1", auth=None).create_item("key: one\n", "config")
        TreeManager(self.ns, "app/cfg2", auth=None).create_item("key: two\n", "config")
        self.cfg1 = Config.objects.get(namespace=self.ns, path="app/cfg1")
        self.folder = TreeItem.objects.get(namespace=self.ns, path="app", node_type="folder")

    def test_for_item_matches_path_based_init(self):
        by_path = TreeManager(self.ns, "app/cfg1", auth=None)
        by_item = TreeManager.for_item(self.ns, self.cfg1, auth=None)

        self.assertEqual(by_path.path, by_item.path)
        self.assertEqual(by_path.item_type, by_item.item_type)
        self.assertEqual(by_path.item.pk, by_item.item.pk)
        self.assertEqual(
            by_path.is_folder_resolvable,
            by_item.is_folder_resolvable,
        )

    def test_for_item_accepts_folder_tree_item(self):
        tm = TreeManager.for_item(self.ns, self.folder, auth=None)

        self.assertEqual(tm.path, "app")
        self.assertEqual(tm.item_type, "folder")
        self.assertEqual(tm.item.node_type, "folder")

    def test_for_item_rejects_namespace_mismatch(self):
        other_ns = create_test_namespace("for-item-other", description="other")

        with self.assertRaises(ValidationError):
            TreeManager.for_item(other_ns, self.cfg1, auth=None)

    def test_list_configs_under_folder_avoids_treeitem_refetch(self):
        folder_tm = TreeManager.for_item(self.ns, self.folder, auth=None)

        with CaptureQueriesContext(connection) as ctx:
            configs = folder_tm.list_configs_under_folder(
                ignore_configs_with_missing_tags=True,
                version="latest",
            )

        self.assertEqual({cfg.path for cfg in configs}, {"app/cfg1", "app/cfg2"})
        # One bulk config query plus per-config version tag resolution (no TreeManager.for_item N+1).
        self.assertLessEqual(len(ctx.captured_queries), 3)

    def test_delete_latest_tagged_version_updates_latest_pointer(self):
        TreeManager(self.ns, "app/cfg1", auth=None).update_item("key: two\n")
        cfg = Config.objects.get(namespace=self.ns, path="app/cfg1")
        self.assertEqual(cfg.tags["latest"], 2)

        TreeManager(self.ns, "app/cfg1", auth=None).delete_item(preview=False, version="2")

        cfg.refresh_from_db()
        self.assertEqual(cfg.tags["latest"], 1)
        deleted_version = cfg.versions.get(version=2)
        self.assertIsNotNone(deleted_version.deleted_at)

    def test_delete_item_by_custom_tag(self):
        TreeManager(self.ns, "app/cfg1", auth=None).update_item("key: two\n")
        cfg = Config.objects.get(namespace=self.ns, path="app/cfg1")
        cfg.tags["pinned"] = 2
        cfg.save(update_fields=["tags"])

        TreeManager(self.ns, "app/cfg1", auth=None).delete_item(preview=False, version="pinned")

        deleted_version = cfg.versions.get(version=2)
        self.assertIsNotNone(deleted_version.deleted_at)

    def test_resolve_version_treats_deleted_version_as_not_found(self):
        TreeManager(self.ns, "app/cfg1", auth=None).update_item("key: two\n")
        TreeManager(self.ns, "app/cfg1", auth=None).delete_item(preview=False, version=2)

        cfg = Config.objects.get(namespace=self.ns, path="app/cfg1")
        cfg.tags["pinned"] = 2
        cfg.save(update_fields=["tags"])

        tm = TreeManager(self.ns, "app/cfg1", auth=None)

        from core.exceptions import VersionNotFound

        with self.assertRaises(VersionNotFound):
            tm.resolve_version(cfg, "2")

        with self.assertRaises(VersionNotFound):
            tm.resolve_version(cfg, "pinned")

    def test_move_single_config(self):
        moved = TreeManager(self.ns, "app/cfg1", auth=None).move_item("moved/cfg1")

        self.assertEqual(moved.path, "moved/cfg1")
        self.assertEqual(moved.name, "cfg1")
        self.assertTrue(Config.objects.filter(namespace=self.ns, path="moved/cfg1").exists())
        self.assertFalse(Config.objects.filter(namespace=self.ns, path="app/cfg1").exists())
        self.assertTrue(
            TreeItem.objects.filter(namespace=self.ns, path="app", node_type="folder").exists(),
            "sibling folder should keep parent folder alive",
        )

    def test_move_rename_in_same_folder_updates_name(self):
        moved = TreeManager(self.ns, "app/cfg1", auth=None).move_item("app/cfg1-renamed")

        self.assertEqual(moved.path, "app/cfg1-renamed")
        self.assertEqual(moved.name, "cfg1-renamed")

    def test_move_to_namespace_root_clears_parent(self):
        moved = TreeManager(self.ns, "app/cfg1", auth=None).move_item("cfg1")

        self.assertEqual(moved.path, "cfg1")
        self.assertEqual(moved.name, "cfg1")
        self.assertIsNone(moved.parent)

    def test_move_folder_allows_destination_with_matching_suffix_segment(self):
        TreeManager(self.ns, "tagtest/cfg", auth=None).create_item("key: x\n", "config")

        moved = TreeManager(self.ns, "tagtest", auth=None).move_item("test/tagtest")

        self.assertEqual(moved.path, "test/tagtest")
        self.assertEqual(moved.name, "tagtest")
        self.assertTrue(Config.objects.filter(namespace=self.ns, path="test/tagtest/cfg").exists())
        self.assertFalse(TreeItem.objects.filter(namespace=self.ns, path="tagtest").exists())

    def test_move_folder_rejects_move_into_descendant_path(self):
        from core.exceptions import WrongMoveTargetException

        with self.assertRaises(WrongMoveTargetException):
            TreeManager(self.ns, "app", auth=None).move_item("app/sub")

    def test_copy_config_to_full_destination_path(self):
        result = TreeManager(self.ns, "app/cfg1", auth=None).copy_item("moved/cfg1")

        self.assertIn("moved/cfg1", result["created"])
        self.assertTrue(Config.objects.filter(namespace=self.ns, path="moved/cfg1").exists())
        self.assertTrue(Config.objects.filter(namespace=self.ns, path="app/cfg1").exists())

    def test_copy_folder_subtree(self):
        result = TreeManager(self.ns, "app", auth=None).copy_item("moved/app")

        self.assertIn("moved/app/cfg1", result["created"])
        self.assertIn("moved/app/cfg2", result["created"])
        self.assertTrue(Config.objects.filter(namespace=self.ns, path="moved/app/cfg1").exists())
        self.assertTrue(Config.objects.filter(namespace=self.ns, path="moved/app/cfg2").exists())

    def test_copy_resolver_to_new_path(self):
        from core.models import Resolver

        TreeManager(self.ns, "app/svc", auth=None).create_item('{"scope":"app"}', "resolver")
        source = Resolver.objects.get(namespace=self.ns, path="app/svc")

        result = TreeManager(self.ns, "app/svc", auth=None).copy_item("other/svc")

        self.assertIn("other/svc", result["created"])
        copied = Resolver.objects.get(namespace=self.ns, path="other/svc")
        self.assertEqual(copied.configuration, source.configuration)
        self.assertTrue(Resolver.objects.filter(namespace=self.ns, path="app/svc").exists())
        self.assertIsNotNone(copied.token1_lookup)
        self.assertNotEqual(copied.token1_lookup, source.token1_lookup)

    def test_delete_custom_config_tag(self):
        from core.schemas.requests import TagPayload

        TreeManager(self.ns, "app/cfg1", auth=None).set_item_tag(
            TagPayload(tag="demo", version=1),
        )
        TreeManager(self.ns, "app/cfg1", auth=None).delete_config_tag("demo")

        cfg = Config.objects.get(namespace=self.ns, path="app/cfg1")
        self.assertNotIn("demo", cfg.tags)

    def test_update_resolver_configuration(self):
        TreeManager(self.ns, "app/svc", auth=None).create_item("{}", "resolver")

        updated = TreeManager(self.ns, "app/svc", auth=None).update_item(
            '{"cast": {"format": "raw"}}',
        )

        self.assertEqual(
            json.loads(updated.configuration),
            {"cast": {"format": "raw"}},
        )
