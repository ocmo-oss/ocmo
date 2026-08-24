"""Unit tests for audit operation label helpers."""

from django.test import SimpleTestCase

from core.constants.audit_operations import OP_PROPAGATE_CONFIG
from core.managers.audit import AuditEventDraft
from core.managers.audit.timeline import format_timeline_note, infer_operation
from core.managers.tree import TreeManager
from core.models import AuditEvent
from core.shortcuts import is_version_number_ref, tag_subresource_from_ref


class TestAuditOperations(SimpleTestCase):
    def test_is_version_number_ref(self):
        self.assertTrue(is_version_number_ref("11"))
        self.assertFalse(is_version_number_ref("latest"))
        self.assertFalse(is_version_number_ref("v11"))

    def test_tag_subresource_from_ref(self):
        self.assertEqual(tag_subresource_from_ref("latest"), ("tag", "latest"))
        self.assertIsNone(tag_subresource_from_ref("3"))

    def test_format_subresource_rejects_version(self):
        with self.assertRaises(ValueError):
            TreeManager.format_subresource(["version"], ["11"])

    def test_infer_resolve_kinds(self):
        draft = AuditEventDraft(event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST)
        self.assertEqual(infer_operation(draft), "Resolve")
        draft = AuditEventDraft(event_kind=AuditEvent.EVENT_KIND_RESOLVE_PARTICIPANT)
        self.assertEqual(infer_operation(draft), "Referenced in resolve")

    def test_infer_read_typed(self):
        draft = AuditEventDraft(
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            http_method="GET",
            api_endpoint="/api/v1/ns/qa/~get/app/cfg",
            object_type="config",
        )
        self.assertEqual(infer_operation(draft), "Read config")

    def test_infer_uses_explicit_operation(self):
        draft = AuditEventDraft(operation="Set tag")
        self.assertEqual(infer_operation(draft), "Set tag")

    def test_format_timeline_note_resolve(self):
        event = AuditEvent(
            auth_id="user-1",
            auth_email="bob@example.com",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="POST",
            api_endpoint="/api/v1/ns/qa/~resolve/app/cfg",
            event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST,
            object_type="config",
            object_id="app/cfg",
            operation="Resolve",
        )
        self.assertEqual(
            format_timeline_note(event),
            "User bob@example.com resolved this config",
        )

    def test_format_timeline_note_set_tag(self):
        event = AuditEvent(
            auth_id="user-1",
            auth_email="admin@example.com",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="POST",
            api_endpoint="/api/v1/ns/qa/~tag/app/cfg",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="app/cfg",
            operation="Set tag",
            object_version=2,
            subresource_type="tag",
            subresource="tagme",
        )
        self.assertEqual(
            format_timeline_note(event),
            "User admin@example.com set tag `tagme` to version 2",
        )

    def test_format_timeline_note_update_item(self):
        event = AuditEvent(
            auth_id="user-1",
            auth_email="admin@example.com",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="PUT",
            api_endpoint="/api/v1/ns/qa/~config/~update/app/cfg",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="app/cfg",
            operation="Update item",
            object_version=3,
        )
        self.assertEqual(
            format_timeline_note(event),
            "User admin@example.com created new version of config (3)",
        )

    def test_format_timeline_note_with_tag_and_error(self):
        event = AuditEvent(
            auth_id="user-1",
            auth_email="alice@example.com",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="POST",
            api_endpoint="/api/v1/ns/qa/~tag/app/cfg",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="app/cfg",
            operation="Set tag",
            object_version=3,
            subresource_type="tag",
            subresource="stable",
            error="tag already exists",
        )
        self.assertEqual(
            format_timeline_note(event),
            "User alice@example.com set tag `stable` to version 3 — tag already exists",
        )

    def test_format_timeline_note_resolver_actor(self):
        event = AuditEvent(
            auth_id="resolver/app/cfg",
            auth_email=None,
            auth_type=AuditEvent.AUTH_TYPE_RESOLVER,
            http_method="PUT",
            api_endpoint="/api/v1/ns/qa/~config/~update/app/cfg",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="app/cfg",
            operation="Update item",
            object_version=4,
        )
        self.assertEqual(
            format_timeline_note(event),
            "Resolver resolver/app/cfg created new version of config (4)",
        )

    def test_format_timeline_note_manual_propagation(self):
        payload = '{"trigger":"manual","targets":[{"path":"env/dev","version":3},{"path":"env/staging","version":2}]}'
        event = AuditEvent(
            auth_id="user-1",
            auth_email="admin@example.com",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="POST",
            api_endpoint="/api/v1/ns/qa/~propagate/proj/source",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="proj/source",
            operation=OP_PROPAGATE_CONFIG,
            object_version=5,
            subresource_type="trigger",
            subresource=payload,
        )
        self.assertEqual(
            format_timeline_note(event),
            "User admin@example.com manually propagated version 5 to `env/dev`@v3, `env/staging`@v2",
        )

    def test_format_timeline_note_tag_propagation(self):
        payload = '{"trigger":"tag","trigger_tag":"stable","targets":[{"path":"env/dev","version":3}]}'
        event = AuditEvent(
            auth_id="user-1",
            auth_email="admin@example.com",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="POST",
            api_endpoint="/api/v1/ns/qa/~tag/proj/source",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="proj/source",
            operation=OP_PROPAGATE_CONFIG,
            object_version=5,
            subresource_type="trigger",
            subresource=payload,
        )
        self.assertEqual(
            format_timeline_note(event),
            "User admin@example.com propagated by setting tag `stable` to version 5, creating `env/dev`@v3",
        )

    def test_format_timeline_note_legacy_propagation_trigger(self):
        event = AuditEvent(
            auth_id="user-1",
            auth_email="admin@example.com",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="POST",
            api_endpoint="/api/v1/ns/qa/~propagate/proj/source",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="proj/source",
            operation=OP_PROPAGATE_CONFIG,
            object_version=5,
            subresource_type="trigger",
            subresource="manual",
        )
        self.assertEqual(
            format_timeline_note(event),
            "User admin@example.com manually propagated version 5",
        )

    def test_format_timeline_note_manual_propagation_all_unchanged(self):
        payload = '{"trigger":"manual","unchanged":["env/dev","env/staging"]}'
        event = AuditEvent(
            auth_id="user-1",
            auth_email="admin@example.com",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="POST",
            api_endpoint="/api/v1/ns/qa/~propagate/proj/source",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="proj/source",
            operation=OP_PROPAGATE_CONFIG,
            object_version=9,
            subresource_type="trigger",
            subresource=payload,
        )
        self.assertEqual(
            format_timeline_note(event),
            "User admin@example.com manually propagated version 9; "
            "all targets already matched (`env/dev`, `env/staging`)",
        )
