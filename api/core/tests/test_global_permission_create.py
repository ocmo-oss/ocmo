"""Tests for Global Permission rule creation and ordering."""

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from core.managers.auth import AuthManager
from core.managers.global_permissions import (
    CATCH_ALL_POSITION,
    GlobalPermissionsManager,
)
from core.models import GlobalPermissionRule
from core.schemas import GlobalPermissionRulePayload


def _read_rule(**claims):
    return {"actors": [{"kind": "User", "claims": claims or {"email": "*"}}]}


@override_settings(
    OIDC_GLOBAL_ADMIN_CLAIM="email",
    OIDC_GLOBAL_ADMIN_VALUE="admin@example.com",
)
class TestGlobalPermissionCreate(TestCase):
    def setUp(self) -> None:
        self.auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        self.mgr = GlobalPermissionsManager(auth=self.auth)
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={"namespace": "first-*", "read": _read_rule()},
        )

    def test_create_without_position_appends(self) -> None:
        payload = GlobalPermissionRulePayload(
            namespace="second-*",
            read=_read_rule(),
        )
        rule = self.mgr.create(payload)
        self.assertEqual(rule.position, 2.0)
        self.assertEqual(rule.rule["namespace"], "second-*")

    def test_create_after_catch_all_at_fixed_position(self) -> None:
        GlobalPermissionRule.objects.create(
            position=CATCH_ALL_POSITION,
            rule={"namespace": "*", "read": _read_rule()},
        )
        payload = GlobalPermissionRulePayload(namespace="dev-*", read=_read_rule())
        rule = self.mgr.create(payload)
        self.assertEqual(rule.position, 2.0)
        self.assertEqual(
            [row.rule.get("namespace") for row in GlobalPermissionRule.objects.order_by("position", "id")],
            ["first-*", "dev-*", "*"],
        )

    def test_create_then_move_before_catch_all(self) -> None:
        GlobalPermissionRule.objects.create(
            position=CATCH_ALL_POSITION,
            rule={"namespace": "*", "read": _read_rule()},
        )
        created = self.mgr.create(
            GlobalPermissionRulePayload(namespace="dev-*", read=_read_rule()),
        )
        moved = self.mgr.move(str(created.id), 1.0)
        self.assertEqual(moved.position, 1.0)
        self.assertEqual(
            [row.rule.get("namespace") for row in GlobalPermissionRule.objects.order_by("position", "id")],
            ["dev-*", "first-*", "*"],
        )

    def test_create_catch_all_uses_fixed_position(self) -> None:
        payload = GlobalPermissionRulePayload(
            namespace="*",
            read=_read_rule(),
        )
        rule = self.mgr.create(payload)
        self.assertEqual(rule.position, CATCH_ALL_POSITION)

    def test_create_after_catch_all_appends_before_fixed_position(self) -> None:
        GlobalPermissionRule.objects.create(
            position=CATCH_ALL_POSITION,
            rule={"namespace": "*", "read": _read_rule()},
        )
        payload = GlobalPermissionRulePayload(
            namespace="another-*",
            read=_read_rule(),
        )
        rule = self.mgr.create(payload)
        self.assertEqual(rule.position, 2.0)

    def test_move_catch_all_ignores_requested_position(self) -> None:
        catch_all = GlobalPermissionRule.objects.create(
            position=CATCH_ALL_POSITION,
            rule={"namespace": "*", "read": _read_rule()},
        )
        moved = self.mgr.move(str(catch_all.id), 1.5)
        self.assertEqual(moved.position, CATCH_ALL_POSITION)

    def test_move_non_catch_all_rejects_position_at_or_above_fixed_slot(self) -> None:
        payload = GlobalPermissionRulePayload(namespace="third-*", read=_read_rule())
        rule = self.mgr.create(payload)
        with self.assertRaises(ValidationError):
            self.mgr.move(str(rule.id), CATCH_ALL_POSITION)

    def test_update_to_catch_all_sets_fixed_position(self) -> None:
        rule = self.mgr.create(
            GlobalPermissionRulePayload(namespace="team-*", read=_read_rule()),
        )
        updated = self.mgr.update(
            str(rule.id),
            GlobalPermissionRulePayload(namespace="*", read=_read_rule()),
        )
        self.assertEqual(updated.position, CATCH_ALL_POSITION)


@override_settings(
    OIDC_GLOBAL_ADMIN_CLAIM="email",
    OIDC_GLOBAL_ADMIN_VALUE="admin@example.com",
)
class TestGlobalPermissionResolveId(TestCase):
    def setUp(self) -> None:
        self.auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        self.mgr = GlobalPermissionsManager(auth=self.auth)
        self.rule = GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "id": "dev-read",
                "namespace": "dev-*",
                "read": _read_rule(),
            },
        )

    def test_get_by_user_defined_id(self) -> None:
        fetched = self.mgr.get("dev-read")
        self.assertEqual(fetched.id, self.rule.id)

    def test_get_by_uuid(self) -> None:
        fetched = self.mgr.get(str(self.rule.id))
        self.assertEqual(fetched.id, self.rule.id)

    def test_update_by_user_defined_id(self) -> None:
        updated = self.mgr.update(
            "dev-read",
            GlobalPermissionRulePayload(
                id="dev-read",
                namespace="dev-*",
                read=_read_rule(email="writer@example.com"),
            ),
        )
        self.assertEqual(updated.rule["read"]["actors"][0]["claims"]["email"], "writer@example.com")

    def test_delete_by_user_defined_id(self) -> None:
        self.mgr.delete("dev-read")
        self.assertFalse(GlobalPermissionRule.objects.filter(id=self.rule.id).exists())

    def test_move_by_user_defined_id(self) -> None:
        other = GlobalPermissionRule.objects.create(
            position=2.0,
            rule={"id": "team-write", "namespace": "team-*", "read": _read_rule()},
        )
        moved = self.mgr.move("dev-read", 2.5)
        self.assertEqual(moved.id, self.rule.id)
        self.assertEqual(moved.position, 2.5)
        other.refresh_from_db()
        self.assertEqual(other.position, 2.0)

    def test_ambiguous_user_defined_id_raises_validation_error(self) -> None:
        GlobalPermissionRule.objects.create(
            position=2.0,
            rule={"id": "dev-read", "namespace": "other-*", "read": _read_rule()},
        )
        with self.assertRaises(ValidationError):
            self.mgr.get("dev-read")
