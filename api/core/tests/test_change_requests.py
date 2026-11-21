"""Change request API tests."""

from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from core.managers.auth import AuthManager
from core.managers.tree import TreeManager
from core.models import GlobalPermissionRule, Namespace
from core.utils.namespace_special_configs import init_namespace_special_configs
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
      - app/**
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "writer@example.com"
    actions:
      - config:write
      - config:read
    resources:
      - app/**
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "admin@example.com"
    actions:
      - "*:*"
    resources:
      - "**"
"""


def _grant_global(ns_name: str) -> None:
    GlobalPermissionRule.objects.create(
        position=1.0,
        rule={
            "namespace": ns_name,
            "read": {"actors": [{"kind": "User", "claims": {"email": "reader@example.com"}}]},
            "write": {
                "actors": [
                    {"kind": "User", "claims": {"email": "writer@example.com"}},
                    {"kind": "User", "claims": {"email": "admin@example.com"}},
                ]
            },
        },
    )


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class ChangeRequestTestCase(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.client = Client()
        self.ns = Namespace.objects.create(
            name="cr-test-ns",
            description="test",
            change_requests_enabled=True,
            change_requests_max_open_per_user_per_resource=5,
        )
        init_namespace_special_configs(self.ns)
        _grant_global(self.ns.name)
        TreeManager(self.ns, "_permissions", auth=None).update_item(_POLICIES)
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: v1\n", "config")

    def _user_auth(self, email: str) -> AuthManager:
        return AuthManager({"_type": "user", "email": email, "name": email.split("@")[0]})

    def _patch_auth(self, email: str):
        return patch(
            "core.managers.auth.AuthManager.from_request",
            return_value=self._user_auth(email),
        )

    def test_reader_can_create_cr(self):
        with self._patch_auth("reader@example.com"):
            resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: cr1\n",
                content_type="text/plain",
            )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["number"], 1)
        self.assertEqual(resp.json()["status"], "open")

    def test_list_requires_item_path_in_url(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: cr1\n",
                content_type="text/plain",
            )
            list_resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~list/",
            )
            root_resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/",
            )
        self.assertEqual(list_resp.status_code, 200, list_resp.content)
        numbers = {item["number"] for item in list_resp.json()["items"]}
        self.assertEqual(numbers, {1})
        self.assertEqual(root_resp.status_code, 404, root_resp.content)

    def test_create_requires_non_empty_title(self):
        with self._patch_auth("reader@example.com"):
            missing = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg",
                data="key: no-title\n",
                content_type="text/plain",
            )
            blank = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=%20%20",
                data="key: blank-title\n",
                content_type="text/plain",
            )
        self.assertEqual(missing.status_code, 422, missing.content)
        self.assertEqual(blank.status_code, 409, blank.content)

    def test_create_with_description_adds_discussion_comment(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=My+CR&description=Context+here",
                data="key: cr-desc\n",
                content_type="text/plain",
            )
            list_resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/?number=1",
            )
        self.assertEqual(list_resp.status_code, 200, list_resp.content)
        items = list_resp.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["body"], "Context here")

    def test_diff_change_request(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: cr-diff\n",
                content_type="text/plain",
            )
            resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~diff/?number=1&against=base&reveal=true",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["to_side"]["requested"], "~1")
        self.assertEqual(body["from_side"]["version"], 1)
        self.assertIn("cr-diff", body["to_side"]["data"])
        self.assertFalse(body["identical"])

    def test_create_rejects_content_identical_to_base(self):
        with self._patch_auth("reader@example.com"):
            resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: v1\n",
                content_type="text/plain",
            )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("base version", resp.json()["error"].lower())

    def test_update_rejects_content_identical_to_base(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: changed\n",
                content_type="text/plain",
            )
            resp = self.client.put(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?number=1",
                data="key: v1\n",
                content_type="text/plain",
            )
        self.assertEqual(resp.status_code, 409)

    def test_update_allows_draft_unused_parameter_reports_in_issues(self):
        draft = (
            "_ocmo:\n"
            "  parameters:\n"
            "    app_name:\n"
            "      type: dynamic\n"
            "      value: myapp\n"
            "      description: Application name\n"
            "key: only_value\n"
        )
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: draft\n",
                content_type="text/plain",
            )
            put_resp = self.client.put(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?number=1",
                data=draft,
                content_type="text/plain",
            )
            get_resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?number=1",
            )
        self.assertEqual(put_resp.status_code, 200, put_resp.content)
        issues = get_resp.json().get("issues") or []
        self.assertTrue(any("app_name" in i for i in issues))

    def test_author_can_patch_title(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: t\n",
                content_type="text/plain",
            )
            resp = self.client.patch(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?number=1",
                data={"title": "My CR"},
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["title"], "My CR")

    def test_apply_requires_approval(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: cr2\n",
                content_type="text/plain",
            )
        with self._patch_auth("writer@example.com"):
            resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~apply/?number=1",
            )
        self.assertEqual(resp.status_code, 409)

    def test_referenced_by_lists_open_peer_cr(self):
        TreeManager(self.ns, "app/other", auth=None).create_item("key: other\n", "config")
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Target",
                data="key: target\n",
                content_type="text/plain",
            )
            peer_body = "_ocmo:\n  extend:\n    configs:\n      - app/cfg@~1\nkey: peer\n"
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/other?title=Peer",
                data=peer_body,
                content_type="text/plain",
            )
            resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?number=1",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        refs = resp.json()["referenced_by"]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["path"], "app/other")
        self.assertEqual(refs[0]["number"], 1)
        peer_resp = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~change-requests/app/other?number=1",
        )
        self.assertEqual(peer_resp.status_code, 200, peer_resp.content)
        deps = peer_resp.json()["depends_on"]
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["path"], "app/cfg")
        self.assertEqual(deps[0]["number"], 1)

    def test_approver_can_unapprove(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: unapprove\n",
                content_type="text/plain",
            )
        with self._patch_auth("writer@example.com"):
            approve = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~approve/?number=1",
            )
            self.assertEqual(approve.status_code, 200, approve.content)
            self.assertIn("writer", approve.json()["approvers"])
            unapprove = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~unapprove/?number=1",
            )
            self.assertEqual(unapprove.status_code, 200, unapprove.content)
            body = unapprove.json()
            self.assertEqual(body["approvers"], [])
            self.assertFalse(body["can_unapprove"])
            self.assertTrue(body["can_approve"])

    def test_apply_after_approve(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: merged\n",
                content_type="text/plain",
            )
        with self._patch_auth("writer@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~approve/?number=1",
            )
            resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~apply/?number=1",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "applied")
        self.assertEqual(resp.json()["applied_version"], 2)

    def test_feature_disabled_returns_404(self):
        self.ns.change_requests_enabled = False
        self.ns.save()
        with self._patch_auth("reader@example.com"):
            resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?number=1",
            )
        self.assertEqual(resp.status_code, 404)

    def test_comment_create_and_list(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: cr-comment\n",
                content_type="text/plain",
            )
            post_resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/?number=1",
                data={"body": "Looks good"},
                content_type="application/json",
            )
            list_resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/?number=1",
            )
        self.assertEqual(post_resp.status_code, 201, post_resp.content)
        self.assertEqual(list_resp.status_code, 200, list_resp.content)
        items = list_resp.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["body"], "Looks good")

    def test_author_can_update_and_delete_comment(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: cr-comment-edit\n",
                content_type="text/plain",
            )
            post_resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/?number=1",
                data={"body": "First"},
                content_type="application/json",
            )
            comment_id = post_resp.json()["id"]
            patch_resp = self.client.patch(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/{comment_id}?number=1",
                data={"body": "Updated"},
                content_type="application/json",
            )
            del_resp = self.client.delete(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/{comment_id}?number=1",
            )
            list_resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/?number=1",
            )
        self.assertEqual(patch_resp.status_code, 200, patch_resp.content)
        self.assertEqual(patch_resp.json()["body"], "Updated")
        self.assertEqual(del_resp.status_code, 204, del_resp.content)
        self.assertEqual(list_resp.json()["total"], 0)

    def test_comments_blocked_on_rejected_cr(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: closed\n",
                content_type="text/plain",
            )
        with self._patch_auth("writer@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~reject/?number=1",
                data={"reason": "no"},
                content_type="application/json",
            )
        with self._patch_auth("reader@example.com"):
            post_resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/?number=1",
                data={"body": "too late"},
                content_type="application/json",
            )
        self.assertEqual(post_resp.status_code, 409, post_resp.content)

    def test_get_includes_approval_events(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: ev\n",
                content_type="text/plain",
            )
        with self._patch_auth("writer@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~approve/?number=1",
            )
            resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?number=1",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        events = resp.json()["approval_events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["approver"], "writer")

    def test_diff_rejected_change_request(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: reject-diff\n",
                content_type="text/plain",
            )
        with self._patch_auth("writer@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~reject/?number=1",
                data={"reason": "no"},
                content_type="application/json",
            )
            resp = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~diff/?number=1&against=base&reveal=true",
            )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("reject-diff", resp.json()["to_side"]["data"])

    def test_non_author_cannot_update_comment(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Test+CR",
                data="key: x\n",
                content_type="text/plain",
            )
            post_resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/?number=1",
                data={"body": "mine"},
                content_type="application/json",
            )
            comment_id = post_resp.json()["id"]
        with self._patch_auth("writer@example.com"):
            patch_resp = self.client.patch(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~comments/{comment_id}?number=1",
                data={"body": "stolen"},
                content_type="application/json",
            )
        self.assertEqual(patch_resp.status_code, 403, patch_resp.content)

    def test_apply_leaves_sibling_open_cr_on_same_item(self):
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=First",
                data="key: first\n",
                content_type="text/plain",
            )
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Second",
                data="key: second\n",
                content_type="text/plain",
            )
        with self._patch_auth("writer@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~approve/?number=1",
            )
            apply_resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~apply/?number=1",
            )
            sibling = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?number=2",
            )
        self.assertEqual(apply_resp.status_code, 200, apply_resp.content)
        self.assertEqual(apply_resp.json()["status"], "applied")
        self.assertEqual(sibling.status_code, 200, sibling.content)
        self.assertEqual(sibling.json()["status"], "open")

    def test_apply_empty_content_is_rejected(self):
        TreeManager(self.ns, "app/empty", auth=None).create_item("key: has-content\n", "config")
        with self._patch_auth("reader@example.com"):
            create = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/empty?title=Empty",
                data="",
                content_type="text/plain",
            )
            self.assertEqual(create.status_code, 201, create.content)
        with self._patch_auth("writer@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/empty/~approve/?number=1",
            )
            resp = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/empty/~apply/?number=1",
            )
        self.assertEqual(resp.status_code, 409, resp.content)

    def test_apply_rewrites_relative_peer_cr_ref(self):
        TreeManager(self.ns, "app/deep/peer", auth=None).create_item("key: peer-base\n", "config")
        with self._patch_auth("reader@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg?title=Target",
                data="key: target\n",
                content_type="text/plain",
            )
            peer_body = "_ocmo:\n  extend:\n    configs:\n      - ../cfg@~1\nkey: peer\n"
            peer_create = self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/deep/peer?title=Peer",
                data=peer_body,
                content_type="text/plain",
            )
            self.assertEqual(peer_create.status_code, 201, peer_create.content)
        with self._patch_auth("writer@example.com"):
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~approve/?number=1",
            )
            self.client.post(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/cfg/~apply/?number=1",
            )
            peer = self.client.get(
                f"/api/v1/ns/{self.ns.name}/~change-requests/app/deep/peer?number=1&include_content=true",
            )
        self.assertEqual(peer.status_code, 200, peer.content)
        content = peer.json()["content"]
        self.assertIn("../cfg@2", content)
        self.assertNotIn("@~1", content)
