import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from core.models import TreeLock
from core.tests.namespace_helpers import create_test_namespace


class TreeLockApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("locktest", description="test")
        self._create_config("app/cfg", b"key: one\n")
        self._create_config("app/sibling", b"key: two\n")
        self._create_config("other/cfg", b"key: three\n")

    def _create_config(self, path: str, body: bytes):
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/{path}",
            data=body,
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def _update_config(self, path: str, body: bytes):
        return self.client.put(
            f"/api/v1/ns/{self.ns.name}/~config/~update/{path}",
            data=body,
            content_type="application/yaml",
        )

    def _create_lock(self, path: str, reason: str = "freeze", expires_at=None):
        body = {"reason": reason}
        if expires_at is not None:
            body["expires_at"] = expires_at.isoformat().replace("+00:00", "Z")
        return self.client.post(
            f"/api/v1/ns/{self.ns.name}/~lock/{path}",
            data=json.dumps(body),
            content_type="application/json",
        )

    def _delete_lock(self, path: str):
        return self.client.delete(f"/api/v1/ns/{self.ns.name}/~lock/{path}")

    def test_lock_crud_and_list(self):
        created = self._create_lock("app", "prod freeze")
        self.assertEqual(created.status_code, 201, created.content)
        payload = created.json()
        self.assertEqual(payload["path"], "app")
        self.assertEqual(payload["reason"], "prod freeze")

        got = self.client.get(f"/api/v1/ns/{self.ns.name}/~lock/app")
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()["reason"], "prod freeze")

        listed = self.client.get(f"/api/v1/ns/{self.ns.name}/~lock/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)

        replaced = self.client.put(
            f"/api/v1/ns/{self.ns.name}/~lock/app",
            data=json.dumps({"reason": "extended freeze"}),
            content_type="application/json",
        )
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(replaced.json()["reason"], "extended freeze")

        deleted = self._delete_lock("app")
        self.assertEqual(deleted.status_code, 204)
        missing = self.client.get(f"/api/v1/ns/{self.ns.name}/~lock/app")
        self.assertEqual(missing.status_code, 404)

    def test_create_lock_requires_existing_path(self):
        response = self._create_lock("missing/path")
        self.assertEqual(response.status_code, 404)

    def test_create_lock_conflict(self):
        self.assertEqual(self._create_lock("app").status_code, 201)
        again = self._create_lock("app")
        self.assertEqual(again.status_code, 409)

    def test_replace_missing_lock_returns_404(self):
        response = self.client.put(
            f"/api/v1/ns/{self.ns.name}/~lock/app",
            data=json.dumps({"reason": "nope"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_covering_lock_blocks_descendant_update(self):
        self.assertEqual(self._create_lock("app").status_code, 201)
        blocked = self._update_config("app/cfg", b"key: changed\n")
        self.assertEqual(blocked.status_code, 423)
        self.assertIn("lock_path", blocked.json())

        allowed = self._update_config("other/cfg", b"key: ok\n")
        self.assertEqual(allowed.status_code, 200)

    def test_update_allowed_after_unlock(self):
        self.assertEqual(self._create_lock("app").status_code, 201)
        self.assertEqual(self._delete_lock("app").status_code, 204)
        response = self._update_config("app/cfg", b"key: changed\n")
        self.assertEqual(response.status_code, 200)

    def test_expired_lock_does_not_block(self):
        past = timezone.now() - timedelta(hours=1)
        TreeLock.objects.create(
            namespace=self.ns,
            path="app",
            reason="old",
            expires_at=past,
        )
        response = self._update_config("app/cfg", b"key: changed\n")
        self.assertEqual(response.status_code, 200)

    def test_list_omits_expired_locks(self):
        TreeLock.objects.create(
            namespace=self.ns,
            path="app",
            reason="old",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        TreeLock.objects.create(
            namespace=self.ns,
            path="other",
            reason="active",
        )
        listed = self.client.get(f"/api/v1/ns/{self.ns.name}/~lock/")
        self.assertEqual(listed.status_code, 200)
        body = listed.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["locks"][0]["path"], "other")

    def test_get_and_resolve_unaffected(self):
        self.assertEqual(self._create_lock("app").status_code, 201)
        got = self.client.get(f"/api/v1/ns/{self.ns.name}/~get/app/cfg")
        self.assertEqual(got.status_code, 200)
        resolved = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve/app/cfg")
        self.assertEqual(resolved.status_code, 200)

    def test_tag_blocked_under_lock(self):
        self.assertEqual(self._create_lock("app/cfg").status_code, 201)
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~tag/app/cfg",
            data=json.dumps({"tag": "release", "version": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 423)

    def test_mark_stable_blocked_under_lock(self):
        self.assertEqual(self._create_lock("app/cfg").status_code, 201)
        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~resolve/app/cfg?mark-stable=true")
        self.assertEqual(response.status_code, 423)

    def test_create_under_locked_parent_blocked(self):
        self.assertEqual(self._create_lock("app").status_code, 201)
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/new",
            data=b"key: new\n",
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 423)

    def test_delete_blocked_under_lock(self):
        self.assertEqual(self._create_lock("app/cfg").status_code, 201)
        response = self.client.delete(f"/api/v1/ns/{self.ns.name}/~delete/app/cfg?preview=false")
        self.assertEqual(response.status_code, 423)

    def test_move_blocked_when_destination_locked(self):
        self.assertEqual(self._create_lock("other").status_code, 201)
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~move/app/cfg",
            data=json.dumps({"target_path": "other/moved"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 423)

    def test_move_folder_blocked_when_child_locked(self):
        self.assertEqual(self._create_lock("app/cfg").status_code, 201)
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~move/app",
            data=json.dumps({"target_path": "other/app"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 423)
        self.assertIn("lock_path", response.json())

    def test_describe_blocked_under_lock(self):
        self.assertEqual(self._create_lock("app/cfg").status_code, 201)
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~describe/app/cfg",
            data=json.dumps({"description": "frozen"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 423)

    def test_recreate_lock_after_expiry(self):
        TreeLock.objects.create(
            namespace=self.ns,
            path="app",
            reason="old",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        response = self._create_lock("app", "new freeze")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["reason"], "new freeze")
        self.assertEqual(TreeLock.objects.filter(namespace=self.ns, path="app").count(), 1)
