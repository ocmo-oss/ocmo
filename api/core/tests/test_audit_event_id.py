"""Tests for audit event id prefix resolution."""

from __future__ import annotations

import uuid

from django.test import TestCase

from core.exceptions import NotFound
from core.managers.audit import AuditManager
from core.managers.auth import AuthManager
from core.models import AuditEvent
from core.tests.namespace_helpers import create_test_namespace


def _admin_auth() -> AuthManager:
    return AuthManager(
        {"_type": "user", "sub": "admin-1", "email": "admin@example.com", "groups": "ocmo-global-admins"}
    )


class TestAuditEventIdResolution(TestCase):
    def setUp(self) -> None:
        AuditManager.unbind()
        self.ns = create_test_namespace("audit-id-prefix")
        self.event = AuditEvent.objects.create(
            namespace_name=self.ns.name,
            auth_id="user-1",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="GET",
            api_endpoint="/api/v1/test",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="app/cfg",
            operation="Read config",
        )

    def tearDown(self) -> None:
        AuditManager.unbind()

    def test_resolve_event_id_accepts_full_uuid(self) -> None:
        mgr = AuditManager(auth=_admin_auth(), namespace=self.ns)
        resolved = mgr.resolve_event_id(str(self.event.id))
        self.assertEqual(resolved, self.event.id)

    def test_resolve_event_id_accepts_unique_prefix(self) -> None:
        mgr = AuditManager(auth=_admin_auth(), namespace=self.ns)
        prefix = str(self.event.id).replace("-", "")[:8]
        resolved = mgr.resolve_event_id(prefix)
        self.assertEqual(resolved, self.event.id)

    def test_resolve_event_id_rejects_ambiguous_prefix(self) -> None:
        AuditEvent.objects.create(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            namespace_name=self.ns.name,
            auth_id="user-1",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="GET",
            api_endpoint="/api/v1/test",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="app/other",
            operation="Read config",
        )
        AuditEvent.objects.create(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaab"),
            namespace_name=self.ns.name,
            auth_id="user-1",
            auth_type=AuditEvent.AUTH_TYPE_USER,
            http_method="GET",
            api_endpoint="/api/v1/test",
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
            object_type="config",
            object_id="app/other2",
            operation="Read config",
        )

        mgr = AuditManager(auth=_admin_auth(), namespace=self.ns)
        with self.assertRaises(ValueError, msg="Ambiguous"):
            mgr.resolve_event_id("aaaaaaaa")

    def test_resolve_event_id_not_found(self) -> None:
        mgr = AuditManager(auth=_admin_auth(), namespace=self.ns)
        with self.assertRaises(NotFound):
            mgr.resolve_event_id("deadbeef")

    def test_resolve_event_id_rejects_short_prefix(self) -> None:
        mgr = AuditManager(auth=_admin_auth(), namespace=self.ns)
        with self.assertRaises(ValueError, msg="too short"):
            mgr.resolve_event_id("abc")
