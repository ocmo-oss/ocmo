"""Tests for append-only audit logging."""

from datetime import timedelta
from unittest.mock import patch

from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

from core.api.errors import error_payload
from core.decorators import PermCheck, audit, enrich_audit, require_permissions
from core.exceptions import NotFound, PermissionDenied, TreeItemConflict
from core.managers.audit import AuditManager
from core.managers.auth import AuthManager
from core.managers.namespace import NamespaceManager
from core.managers.resolving import CacheParticipant
from core.managers.tree import TreeManager
from core.models import AuditEvent, GlobalPermissionRule, Namespace
from core.tests.namespace_helpers import create_test_namespace
from core.utils.permissions_compiler import PermissionsCompiler


def _user_auth(**claims):
    raw = {"_type": "user", "sub": "user-1", "email": "bob@example.com", "name": "Bob", **claims}
    return AuthManager(raw)


def _admin_auth():
    return AuthManager(
        {"_type": "user", "sub": "admin-1", "email": "admin@example.com", "groups": "ocmo-global-admins"}
    )


def _bind_request(
    auth: AuthManager,
    *,
    path: str = "/api/v1/ns/test/~config/",
    method: str = "GET",
    namespace=None,
) -> AuthManager:
    AuditManager.unbind()
    factory = RequestFactory()
    request = getattr(factory, method.lower())(path)
    request.auth = auth._raw
    AuditManager.bind(request, auth, namespace=namespace)
    return auth


class TestAuditManager(TestCase):
    def setUp(self):
        AuditManager.unbind()
        self.ns = create_test_namespace("audit-test")

    def tearDown(self):
        AuditManager.unbind()

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_begin_save_creates_event(self):
        _bind_request(_user_auth(), namespace=self.ns)
        AuditManager.current().begin_operation("config", "app/conf").set_outcome(permission_ok=True).save()

        event = AuditEvent.objects.get(object_id="app/conf", event_kind=AuditEvent.EVENT_KIND_OPERATION)
        self.assertEqual(event.namespace_name, "audit-test")
        self.assertEqual(event.event_kind, AuditEvent.EVENT_KIND_OPERATION)
        self.assertEqual(event.auth_email, "bob@example.com")
        self.assertEqual(event.http_method, "GET")
        self.assertTrue(event.permission_ok)

    def test_save_participants(self):
        _bind_request(_user_auth(), namespace=self.ns)
        audit = AuditManager.current()
        assert audit is not None
        audit.begin_resolve_request("root/cfg").set_outcome(permission_ok=True).save()
        parent = audit._last_saved
        self.assertEqual(parent.operation, "Resolve")

        participants = [
            CacheParticipant(kind="config", path="root/cfg", ref="latest", version=1),
            CacheParticipant(kind="secret", path="secrets/db", ref="latest", version=2),
            CacheParticipant(kind="config", path="base/cfg", ref="3", version=3),
        ]
        saved = audit.save_participants(participants, roots={"root/cfg"})
        self.assertEqual(len(saved), 2)

        self.assertFalse(AuditEvent.objects.filter(object_id="root/cfg", event_kind="resolve_participant").exists())
        nested = AuditEvent.objects.get(object_id="secrets/db", event_kind="resolve_participant")
        self.assertEqual(nested.resolve_type, "nested")
        self.assertEqual(nested.operation, "Referenced in resolve")
        self.assertEqual(nested.subresource_type, "tag")
        self.assertEqual(nested.subresource, "latest")
        self.assertEqual(nested.object_version, 2)
        self.assertEqual(nested.parent_event_id, parent.id)

        numeric_ref = AuditEvent.objects.get(object_id="base/cfg", event_kind="resolve_participant")
        self.assertEqual(numeric_ref.object_version, 3)
        self.assertIsNone(numeric_ref.subresource_type)
        self.assertIsNone(numeric_ref.subresource)

    def test_config_resolve_stats(self):
        _bind_request(_user_auth(), namespace=self.ns)
        audit = AuditManager.current()
        assert audit is not None
        now = timezone.now()
        audit.begin_resolve_request("stats/cfg").set_outcome(permission_ok=True).save()
        audit.save_participants(
            [
                CacheParticipant(kind="config", path="stats/cfg", ref="latest", version=1),
                CacheParticipant(kind="config", path="base/cfg", ref="latest", version=1),
            ],
            roots={"stats/cfg"},
        )
        # Same path also referenced as nested from another resolve
        audit.begin_resolve_request("other/cfg").set_outcome(permission_ok=True).save()
        audit.save_participants(
            [
                CacheParticipant(kind="config", path="other/cfg", ref="latest", version=1),
                CacheParticipant(kind="config", path="stats/cfg", ref="latest", version=1),
            ],
            roots={"other/cfg"},
        )

        stats = AuditManager(namespace=self.ns).config_resolve_stats(
            "stats/cfg",
            since=now - timedelta(hours=1),
            until=now + timedelta(hours=1),
        )
        self.assertEqual(stats.direct, 1)
        self.assertEqual(stats.nested, 1)

    def test_resolve_stats_series_buckets(self):
        TreeManager(self.ns, "series/cfg", auth=None).create_item("key: value\n", "config")
        _bind_request(_user_auth(), namespace=self.ns)
        audit = AuditManager.current()
        assert audit is not None
        now = timezone.now()
        since = now - timedelta(days=2)
        until = now + timedelta(hours=1)
        audit.begin_resolve_request("series/cfg").set_outcome(permission_ok=True).save()
        audit.begin_resolve_request("series/cfg").set_outcome(
            permission_ok=True,
            error="validation failed",
        ).save()
        audit.save_participants(
            [
                CacheParticipant(kind="config", path="series/cfg", ref="latest", version=1),
                CacheParticipant(kind="config", path="dep/cfg", ref="latest", version=1),
            ],
            roots={"series/cfg"},
        )
        audit.begin_resolve_request("other/cfg").set_outcome(permission_ok=True).save()
        audit.save_participants(
            [
                CacheParticipant(kind="config", path="series/cfg", ref="latest", version=1),
            ],
            roots={"other/cfg"},
        )

        buckets = AuditManager(namespace=self.ns).resolve_stats_series(
            object_id="series/cfg",
            object_type="config",
            since=since,
            until=until,
            bucket_seconds=24 * 60 * 60,
        )
        self.assertGreaterEqual(len(buckets), 2)
        total_direct = sum(bucket.direct for bucket in buckets)
        total_nested = sum(bucket.nested for bucket in buckets)
        total_errors = sum(bucket.errors for bucket in buckets)
        self.assertEqual(total_direct, 2)
        self.assertEqual(total_nested, 1)
        self.assertEqual(total_errors, 1)

    def test_resolve_stats_series_resolver_auth_only(self):
        TreeManager(self.ns, "app/svc", auth=None).create_item("{}", "resolver")
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: value\n", "config")
        TreeManager(self.ns, "other/cfg", auth=None).create_item("key: value\n", "config")

        def resolver_auth(path: str) -> AuthManager:
            scope = "/".join(path.split("/")[:-1])
            name = path.split("/")[-1]
            return AuthManager(
                {
                    "_type": "resolver",
                    "namespace": self.ns.id,
                    "name": name,
                    "access_scope": scope,
                    "token_number": 1,
                }
            )

        now = timezone.now()
        since = now - timedelta(days=1)
        until = now + timedelta(hours=1)

        _bind_request(resolver_auth("app/svc"), namespace=self.ns)
        audit = AuditManager.current()
        assert audit is not None
        audit.begin_resolve_request("app/cfg").set_outcome(permission_ok=True).save()
        audit.begin_resolve_request("other/cfg").set_outcome(
            permission_ok=True,
            error="failed",
        ).save()
        audit.save_participants(
            [
                CacheParticipant(kind="config", path="app/cfg", ref="latest", version=1),
                CacheParticipant(kind="config", path="dep/cfg", ref="latest", version=1),
            ],
            roots={"app/cfg"},
        )

        _bind_request(_user_auth(), namespace=self.ns)
        audit = AuditManager.current()
        assert audit is not None
        audit.begin_resolve_request("app/cfg").set_outcome(permission_ok=True).save()

        buckets = AuditManager(namespace=self.ns).resolve_stats_series(
            object_id="app/svc",
            object_type="resolver",
            since=since,
            until=until,
            bucket_seconds=24 * 60 * 60,
        )
        total_direct = sum(bucket.direct for bucket in buckets)
        total_nested = sum(bucket.nested for bucket in buckets)
        total_errors = sum(bucket.errors for bucket in buckets)
        self.assertEqual(total_direct, 2)
        self.assertEqual(total_nested, 0)
        self.assertEqual(total_errors, 1)

    def test_resolve_stats_series_folder_aggregate(self):
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: value\n", "config")
        TreeManager(self.ns, "app/nested/cfg", auth=None).create_item("key: value\n", "config")
        TreeManager(self.ns, "other/cfg", auth=None).create_item("key: value\n", "config")

        _bind_request(_user_auth(), namespace=self.ns)
        audit = AuditManager.current()
        assert audit is not None
        now = timezone.now()
        since = now - timedelta(days=1)
        until = now + timedelta(hours=1)

        audit.begin_resolve_request("app/cfg").set_outcome(permission_ok=True).save()
        audit.save_participants(
            [
                CacheParticipant(kind="config", path="app/cfg", ref="latest", version=1),
                CacheParticipant(kind="config", path="dep/cfg", ref="latest", version=1),
            ],
            roots={"app/cfg"},
        )
        audit.begin_resolve_request("app/nested/cfg").set_outcome(permission_ok=True).save()
        audit.begin_resolve_request("other/cfg").set_outcome(permission_ok=True).save()
        audit.save_participants(
            [
                CacheParticipant(kind="config", path="other/cfg", ref="latest", version=1),
                CacheParticipant(kind="config", path="app/cfg", ref="latest", version=1),
            ],
            roots={"other/cfg"},
        )

        buckets = AuditManager(namespace=self.ns).resolve_stats_series(
            object_id="app",
            object_type="folder",
            since=since,
            until=until,
            bucket_seconds=24 * 60 * 60,
        )
        total_direct = sum(bucket.direct for bucket in buckets)
        total_nested = sum(bucket.nested for bucket in buckets)
        self.assertEqual(total_direct, 2)
        self.assertEqual(total_nested, 1)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_operation_inferred_when_not_set(self):
        _bind_request(
            _user_auth(),
            path="/api/v1/ns/audit-test/~get/app/conf",
            method="GET",
            namespace=self.ns,
        )
        AuditManager.current().begin_operation("config", "app/conf").set_outcome(permission_ok=True).save()
        event = AuditEvent.objects.get(object_id="app/conf", event_kind="operation")
        self.assertEqual(event.operation, "Read config")

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_decorator_sets_operation_and_subresource(self):
        class FakeManager:
            def __init__(self, namespace, auth):
                self.namespace = namespace
                self.auth = auth
                self.path = "app/cfg"
                self.item = type("Item", (), {"node_type": "config", "tags": {"latest": 2}})()

            @audit(
                "config",
                operation="Set tag",
                object_version=lambda self, result, bound: bound["payload"].version,
                subresource_type="tag",
                subresource=lambda self, result, bound: bound["payload"].tag,
            )
            def set_tag(self, payload):
                return self.item

        auth = _user_auth()
        _bind_request(
            auth,
            path="/api/v1/ns/audit-test/~tag/app/cfg",
            method="POST",
            namespace=self.ns,
        )
        mgr = FakeManager(self.ns, auth)
        payload = type("Payload", (), {"tag": "mytag", "version": 11})()
        mgr.set_tag(payload)

        event = AuditEvent.objects.get(object_id="app/cfg", operation="Set tag")
        self.assertEqual(event.object_version, 11)
        self.assertEqual(event.subresource_type, "tag")
        self.assertEqual(event.subresource, "mytag")

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_namespace_delete_retains_namespace_name(self):
        _bind_request(_user_auth(), namespace=self.ns)
        ns_name = self.ns.name
        self.ns.delete()
        AuditManager.current().begin_operation("namespace", ns_name).set_outcome(permission_ok=True).save()
        event = AuditEvent.objects.get(object_id=ns_name, object_type="namespace")
        self.assertEqual(event.namespace_name, ns_name)
        self.assertIsNone(event.namespace_id)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_save_clears_namespace_fk_when_namespace_deleted(self):
        _bind_request(_user_auth(), namespace=self.ns)
        audit = AuditManager.current()
        assert audit is not None
        ns_name = self.ns.name
        stale_namespace = self.ns
        stale_namespace.delete()

        audit.begin_operation("config", "app/cfg")
        audit._draft.namespace = stale_namespace
        audit._draft.namespace_name = ns_name
        audit.set_outcome(permission_ok=True).save()

        event = AuditEvent.objects.get(object_id="app/cfg", event_kind=AuditEvent.EVENT_KIND_OPERATION)
        self.assertEqual(event.namespace_name, ns_name)
        self.assertIsNone(event.namespace_id)


class TestAuditDecorator(TestCase):
    def setUp(self):
        AuditManager.unbind()
        self.ns = create_test_namespace("audit-decorator")

    def tearDown(self):
        AuditManager.unbind()

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_decorator_logs_success(self):
        auth = _bind_request(_user_auth(), namespace=self.ns)
        ns = self.ns

        class Mgr:
            namespace = ns
            path = "app/cfg"

            @audit("config")
            @require_permissions(PermCheck("config:read"))
            def read(self):
                return "ok"

        mgr = Mgr()
        mgr.auth = auth
        mgr.read()
        event = AuditEvent.objects.get(object_id="app/cfg", event_kind=AuditEvent.EVENT_KIND_OPERATION)
        self.assertTrue(event.permission_ok)
        self.assertIsNone(event.error)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_decorator_logs_permission_denied(self):
        ns = Namespace.objects.create(name="audit-deny", description="test")
        from core.utils.namespace_special_configs import _load_builtin_schema_content

        TreeManager(ns, "_permissions.schema", auth=None).create_item(
            _load_builtin_schema_content("_permissions.schema"),
            "config",
        )
        TreeManager(ns, "_permissions", auth=None).create_item("policies: []\n", "config")
        auth = _bind_request(
            AuthManager({"_type": "user", "sub": "x", "email": "denied@example.com", "name": "Denied"}),
            namespace=ns,
        )

        class Mgr:
            namespace = ns
            path = "app/cfg"

            @audit("config")
            @require_permissions(PermCheck("config:read"))
            def read(self):
                return "ok"

        mgr = Mgr()
        mgr.auth = auth
        with self.assertRaises(PermissionDenied):
            mgr.read()

        event = AuditEvent.objects.get(object_id="app/cfg", event_kind=AuditEvent.EVENT_KIND_OPERATION)
        self.assertFalse(event.permission_ok)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_decorator_attaches_audit_event_id_on_business_error(self):
        auth = _bind_request(_user_auth(), namespace=self.ns)
        ns = self.ns

        class Mgr:
            namespace = ns
            path = "app/cfg"

            @audit("config")
            def write(self):
                raise TreeItemConflict("Another item by the same path already exists")

        mgr = Mgr()
        mgr.auth = auth
        with self.assertRaises(TreeItemConflict) as ctx:
            mgr.write()

        event = AuditEvent.objects.get(object_id="app/cfg", event_kind=AuditEvent.EVENT_KIND_OPERATION)
        self.assertEqual(event.error, "Another item by the same path already exists")
        self.assertEqual(ctx.exception.audit_event_id, event.id)
        payload = error_payload(ctx.exception, str(ctx.exception))
        self.assertEqual(payload["audit_event_id"], str(event.id))

    def test_internal_call_skipped(self):
        before = AuditEvent.objects.count()

        class Mgr:
            namespace = self.ns
            auth = None
            path = "app/cfg"

            @audit("config")
            @require_permissions(PermCheck("config:read"))
            def read(self):
                return "ok"

        Mgr().read()
        self.assertEqual(AuditEvent.objects.count(), before)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_namespace_get_or_raise_audited_when_bound_first(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "audit-decorator",
                "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
            },
        )
        auth = _user_auth()
        request = RequestFactory().get(f"/api/v1/ns/{self.ns.name}")
        mgr = NamespaceManager(self.ns.name, auth=auth)
        AuditManager.bind(request, auth, namespace=mgr.ns)
        mgr.get_or_raise()
        event = AuditEvent.objects.get(
            object_type="namespace",
            object_id=self.ns.name,
            event_kind=AuditEvent.EVENT_KIND_OPERATION,
        )
        self.assertTrue(event.permission_ok)
        self.assertEqual(event.namespace_name, self.ns.name)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_enrich_audit_sets_fields_on_decorated_method(self):
        auth = _bind_request(_user_auth(), namespace=self.ns)

        class Mgr:
            namespace = self.ns
            path = "app/cfg"

            @audit("config", operation="Update item")
            def write(self):
                enrich_audit(
                    object_version=7,
                    subresource_type="tag",
                    subresource="x",
                )
                return "ok"

        mgr = Mgr()
        mgr.auth = auth
        mgr.write()
        event = AuditEvent.objects.get(object_id="app/cfg", operation="Update item")
        self.assertEqual(event.object_version, 7)
        self.assertEqual(event.subresource_type, "tag")
        self.assertEqual(event.subresource, "x")

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_enrich_audit_noop_without_active_audit(self):
        enrich_audit(object_version=1)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_enrich_audit_overrides_decorator_defaults(self):
        auth = _bind_request(_user_auth(), namespace=self.ns)

        class Mgr:
            namespace = self.ns
            path = "app/cfg"

            @audit("config", operation="Update item", object_version=1)
            def write(self):
                enrich_audit(object_version=9)
                return "ok"

        mgr = Mgr()
        mgr.auth = auth
        mgr.write()
        event = AuditEvent.objects.get(object_id="app/cfg", operation="Update item")
        self.assertEqual(event.object_version, 9)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_nested_decorated_calls_persist_outer_and_inner_audit_events(self):
        auth = _bind_request(
            _user_auth(),
            path="/api/v1/ns/audit-decorator/~propagate/app/cfg",
            method="POST",
            namespace=self.ns,
        )

        class Mgr:
            namespace = self.ns
            path = "app/cfg"

            @audit("config", operation="Propagate config", subresource_type="trigger")
            def propagate(self):
                enrich_audit(
                    object_version=3,
                    subresource='{"trigger":"manual","targets":[{"path":"other/cfg","version":2}]}',
                )
                self.update_target()
                return {"source_version": 3}

            @audit("config", operation="Update item")
            def update_target(self):
                enrich_audit(object_version=2)
                return "ok"

        mgr = Mgr()
        mgr.auth = auth
        mgr.propagate()

        propagate_event = AuditEvent.objects.get(
            object_id="app/cfg",
            operation="Propagate config",
        )
        self.assertEqual(propagate_event.object_version, 3)
        self.assertIn("manual", propagate_event.subresource or "")

        update_event = AuditEvent.objects.get(
            object_id="app/cfg",
            operation="Update item",
        )
        self.assertEqual(update_event.object_version, 2)
        self.assertEqual(AuditEvent.objects.filter(object_id="app/cfg").count(), 2)


class TestNamespaceAuditPermission(TestCase):
    def setUp(self):
        AuditManager.unbind()
        PermissionsCompiler._global_cache.clear()
        self.ns = create_test_namespace("audit-perm")
        self.client = Client()

    def tearDown(self):
        AuditManager.unbind()
        PermissionsCompiler._global_cache.clear()

    def test_compile_global_rules_audit_section(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "audit-*",
                "audit": {"actors": [{"kind": "User", "claims": {"email": "auditor@example.com"}}]},
            },
        )
        auth = AuthManager({"_type": "user", "email": "auditor@example.com"})
        pm = auth.permissions()
        self.assertTrue(pm.check_namespace_object("audit-perm", "audit"))

    def test_audit_list_requires_namespace_audit(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "audit-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "reader@example.com"}}]},
            },
        )
        auth = AuthManager({"_type": "user", "email": "reader@example.com"})
        with self.assertRaises(PermissionDenied):
            AuditManager(auth=auth, namespace=self.ns).list()

    def test_audit_list_allowed_with_audit_permission(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "audit-*",
                "audit": {"actors": [{"kind": "User", "claims": {"email": "auditor@example.com"}}]},
            },
        )
        auth = AuthManager({"_type": "user", "email": "auditor@example.com"})
        self.assertEqual(AuditManager(auth=auth, namespace=self.ns).list().count(), 0)

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_global_admin_can_list_all_audit(self):
        auth = _admin_auth()
        AuditManager(auth=auth).begin_operation("namespace", "other-ns").set_outcome(permission_ok=True).save()
        self.assertEqual(AuditManager(auth=auth).list().count(), 1)


@override_settings(OCMO_AUDIT_MODE="all")
class TestAuditAPI(TestCase):
    def setUp(self):
        AuditManager.unbind()
        PermissionsCompiler._global_cache.clear()
        self.ns = create_test_namespace("audit-api")
        self.client = Client()
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "audit-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                "audit": {"actors": [{"kind": "User", "claims": {"email": "auditor@example.com"}}]},
            },
        )
        _bind_request(
            AuthManager({"_type": "user", "email": "auditor@example.com", "sub": "auditor"}),
            namespace=self.ns,
        )
        AuditManager.current().begin_operation("config", "x").set_outcome(permission_ok=True).save()

    def tearDown(self):
        AuditManager.unbind()
        PermissionsCompiler._global_cache.clear()

    def test_namespace_audit_endpoint_requires_auth(self):
        from core.tests.auth_helpers import deny_authentication

        with deny_authentication():
            resp = self.client.get("/api/v1/ns/audit-api/~audit/")
        self.assertEqual(resp.status_code, 403)

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_tree_create_writes_audit(self):
        auth = _bind_request(
            _user_auth(),
            path="/api/v1/ns/audit-api/~config/~create/new/cfg",
            method="POST",
            namespace=self.ns,
        )
        TreeManager(self.ns, "new/cfg", auth=auth).create_item("key: value\n", "config")
        self.assertTrue(AuditEvent.objects.filter(object_id="new/cfg", object_type="config").exists())


class TestAuditMode(TestCase):
    def setUp(self):
        AuditManager.unbind()
        self.ns = create_test_namespace("audit-mode")

    def tearDown(self):
        AuditManager.unbind()

    @override_settings(OCMO_AUDIT_MODE="resolve")
    def test_resolve_mode_skips_get_operation(self):
        TreeManager(self.ns, "read/cfg", auth=None).create_item("k: v\n", "config")
        auth = _bind_request(_user_auth(), namespace=self.ns)
        TreeManager(self.ns, "read/cfg", auth=auth).get_extended()
        self.assertFalse(AuditEvent.objects.filter(event_kind=AuditEvent.EVENT_KIND_OPERATION).exists())

    @override_settings(OCMO_AUDIT_MODE="resolve")
    def test_resolve_mode_skips_post_operation(self):
        auth = _bind_request(
            _user_auth(),
            path="/api/v1/ns/audit-mode/~config/~create/new/cfg",
            method="POST",
            namespace=self.ns,
        )
        TreeManager(self.ns, "new/cfg", auth=auth).create_item("key: value\n", "config")
        self.assertFalse(AuditEvent.objects.filter(event_kind=AuditEvent.EVENT_KIND_OPERATION).exists())

    @override_settings(OCMO_AUDIT_MODE="resolve")
    def test_resolve_mode_persists_resolve_events(self):
        _bind_request(_user_auth(), namespace=self.ns)
        audit = AuditManager.current()
        assert audit is not None
        audit.begin_resolve_request("root/cfg").set_outcome(permission_ok=True).save()
        self.assertEqual(
            AuditEvent.objects.filter(event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST).count(),
            1,
        )

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_modifications_mode_skips_get_operation(self):
        TreeManager(self.ns, "read/cfg", auth=None).create_item("k: v\n", "config")
        auth = _bind_request(_user_auth(), namespace=self.ns)
        TreeManager(self.ns, "read/cfg", auth=auth).get_extended()
        self.assertFalse(AuditEvent.objects.filter(event_kind=AuditEvent.EVENT_KIND_OPERATION).exists())

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_modifications_mode_persists_post_operation(self):
        auth = _bind_request(
            _user_auth(),
            path="/api/v1/ns/audit-mode/~config/~create/new/cfg",
            method="POST",
            namespace=self.ns,
        )
        TreeManager(self.ns, "new/cfg", auth=auth).create_item("key: value\n", "config")
        self.assertTrue(
            AuditEvent.objects.filter(object_id="new/cfg", event_kind=AuditEvent.EVENT_KIND_OPERATION).exists()
        )

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_modifications_mode_persists_resolve_events(self):
        _bind_request(_user_auth(), namespace=self.ns)
        AuditManager.current().begin_resolve_request("cfg").set_outcome(permission_ok=True).save()
        self.assertEqual(
            AuditEvent.objects.filter(event_kind=AuditEvent.EVENT_KIND_RESOLVE_REQUEST).count(),
            1,
        )

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_all_mode_persists_get_operation(self):
        auth = _bind_request(_user_auth(), namespace=self.ns)
        ns = self.ns

        class Mgr:
            namespace = ns
            path = "app/cfg"

            @audit("config")
            @require_permissions(PermCheck("config:read"))
            def read(self):
                return "ok"

        mgr = Mgr()
        mgr.auth = auth
        mgr.read()
        self.assertTrue(AuditEvent.objects.filter(event_kind=AuditEvent.EVENT_KIND_OPERATION).exists())

    @override_settings(OCMO_AUDIT_MODE="bogus")
    def test_invalid_mode_falls_back_to_resolve(self):
        self.assertEqual(AuditManager.get_audit_mode(), "resolve")
        TreeManager(self.ns, "read/cfg", auth=None).create_item("k: v\n", "config")
        auth = _bind_request(_user_auth(), namespace=self.ns)
        TreeManager(self.ns, "read/cfg", auth=auth).get_extended()
        self.assertFalse(AuditEvent.objects.filter(event_kind=AuditEvent.EVENT_KIND_OPERATION).exists())

    @override_settings(OCMO_AUDIT_MODE="resolve")
    def test_permission_denied_on_get_not_audited_in_resolve_mode(self):
        ns = Namespace.objects.create(name="audit-mode-deny", description="test")
        from core.utils.namespace_special_configs import _load_builtin_schema_content

        TreeManager(ns, "_permissions.schema", auth=None).create_item(
            _load_builtin_schema_content("_permissions.schema"),
            "config",
        )
        TreeManager(ns, "_permissions", auth=None).create_item("policies: []\n", "config")
        auth = _bind_request(
            AuthManager({"_type": "user", "sub": "x", "email": "denied@example.com", "name": "Denied"}),
            namespace=ns,
        )

        class Mgr:
            namespace = ns
            path = "app/cfg"

            @audit("config")
            @require_permissions(PermCheck("config:read"))
            def read(self):
                return "ok"

        mgr = Mgr()
        mgr.auth = auth
        with self.assertRaises(PermissionDenied):
            mgr.read()
        self.assertFalse(AuditEvent.objects.exists())

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_delete_preview_skipped(self):
        TreeManager(self.ns, "del/cfg", auth=None).create_item("k: v\n", "config")
        auth = _bind_request(
            _user_auth(),
            path="/api/v1/ns/audit-mode/~delete/del/cfg",
            method="DELETE",
            namespace=self.ns,
        )
        TreeManager(self.ns, "del/cfg", auth=auth).delete_item(preview=True)
        self.assertFalse(AuditEvent.objects.exists())

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_delete_without_preview_audited(self):
        TreeManager(self.ns, "del/cfg", auth=None).create_item("k: v\n", "config")
        auth = _bind_request(
            _user_auth(),
            path="/api/v1/ns/audit-mode/~delete/del/cfg",
            method="DELETE",
            namespace=self.ns,
        )
        TreeManager(self.ns, "del/cfg", auth=auth).delete_item(preview=False)
        self.assertTrue(
            AuditEvent.objects.filter(
                object_id="del/cfg",
                event_kind=AuditEvent.EVENT_KIND_OPERATION,
            ).exists()
        )

    @override_settings(OCMO_AUDIT_MODE="all")
    def test_delete_preview_skipped_even_in_all_mode(self):
        TreeManager(self.ns, "del/cfg", auth=None).create_item("k: v\n", "config")
        auth = _bind_request(_user_auth(), namespace=self.ns)
        TreeManager(self.ns, "del/cfg", auth=auth).delete_item(preview=True)
        self.assertFalse(AuditEvent.objects.exists())


class TestItemAuditTimeline(TestCase):
    def setUp(self):
        AuditManager.unbind()
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.ns = create_test_namespace("item-audit")
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: value\n", "config")

    def tearDown(self):
        AuditManager.unbind()
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def _policy(self, *, email: str, actions: list[str]):
        return PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    {
                        "effect": "Allow",
                        "actors": [{"kind": "User", "claims": {"email": email}}],
                        "actions": actions,
                        "resources": ["**"],
                    }
                ],
            }
        )

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_item_timeline_requires_item_audit(self):
        ps = self._policy(email="reader@example.com", actions=["config:read"])
        auth = AuthManager({"_type": "user", "email": "reader@example.com"})
        with patch(
            "core.utils.permissions_compiler.PermissionsCompiler.load_policy_set",
            return_value=ps,
        ):
            with self.assertRaises(NotFound):
                AuditManager(auth=auth, namespace=self.ns).item_timeline(
                    "app/cfg",
                    "config",
                )

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_item_timeline_allowed_with_item_audit(self):
        ps = self._policy(email="auditor@example.com", actions=["config:audit"])
        auth = _bind_request(
            AuthManager({"_type": "user", "email": "auditor@example.com"}),
            method="POST",
            path="/api/v1/ns/item-audit/~config/~update/app/cfg",
            namespace=self.ns,
        )
        AuditManager.current().begin_operation("config", "app/cfg").set_operation("Update item").set_outcome(
            permission_ok=True
        ).save()

        with patch(
            "core.utils.permissions_compiler.PermissionsCompiler.load_policy_set",
            return_value=ps,
        ):
            rows = list(AuditManager(auth=auth, namespace=self.ns).item_timeline("app/cfg", "config"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].object_id, "app/cfg")

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_item_timeline_excludes_failed_events(self):
        ps = self._policy(email="auditor@example.com", actions=["config:audit"])
        auth = _bind_request(
            AuthManager({"_type": "user", "email": "auditor@example.com"}),
            method="POST",
            path="/api/v1/ns/item-audit/~config/~update/app/cfg",
            namespace=self.ns,
        )
        AuditManager.current().begin_operation("config", "app/cfg").set_operation("Update item").set_outcome(
            permission_ok=True
        ).save()
        AuditManager.current().begin_operation("config", "app/cfg").set_operation("Set tag").set_outcome(
            permission_ok=True, error="tag already exists"
        ).save()
        AuditManager.current().begin_operation("config", "app/cfg").set_operation("Update item").set_outcome(
            permission_ok=False, error="Permission denied"
        ).save()

        with patch(
            "core.utils.permissions_compiler.PermissionsCompiler.load_policy_set",
            return_value=ps,
        ):
            rows = list(AuditManager(auth=auth, namespace=self.ns).item_timeline("app/cfg", "config"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].operation, "Update item")

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_item_timeline_search_matches_operation(self):
        ps = self._policy(email="auditor@example.com", actions=["config:audit"])
        auth = _bind_request(
            AuthManager({"_type": "user", "email": "auditor@example.com"}),
            method="POST",
            path="/api/v1/ns/item-audit/~config/~update/app/cfg",
            namespace=self.ns,
        )
        AuditManager.current().begin_operation("config", "app/cfg").set_operation("Update item").set_outcome(
            permission_ok=True
        ).save()
        AuditManager.current().begin_resolve_request("app/cfg").set_outcome(permission_ok=True).save()

        with patch(
            "core.utils.permissions_compiler.PermissionsCompiler.load_policy_set",
            return_value=ps,
        ):
            mgr = AuditManager(auth=auth, namespace=self.ns)
            self.assertEqual(mgr.item_timeline("app/cfg", "config").count(), 1)
            self.assertEqual(mgr.item_timeline("app/cfg", "config", search="Update item").count(), 1)
            self.assertEqual(mgr.item_timeline("app/cfg", "config", search="Resolve").count(), 0)
            self.assertEqual(mgr.item_timeline("app/cfg", "config", search="missing").count(), 0)

    @override_settings(OCMO_AUDIT_MODE="modifications-and-resolve")
    def test_item_timeline_includes_events_from_prior_paths_after_move(self):
        ps = self._policy(
            email="auditor@example.com",
            actions=["config:audit", "config:read", "config:delete", "config:write"],
        )
        _bind_request(
            AuthManager({"_type": "user", "email": "auditor@example.com"}),
            method="POST",
            path="/api/v1/ns/item-audit/~config/~update/app/cfg",
            namespace=self.ns,
        )
        AuditManager.current().begin_operation("config", "app/cfg").set_operation("Update item").set_outcome(
            permission_ok=True
        ).save()

        move_auth = _bind_request(
            AuthManager({"_type": "user", "email": "auditor@example.com"}),
            method="POST",
            path="/api/v1/ns/item-audit/~move/app/cfg",
            namespace=self.ns,
        )
        TreeManager(self.ns, "app/cfg", auth=move_auth).move_item("moved/cfg")

        with patch(
            "core.utils.permissions_compiler.PermissionsCompiler.load_policy_set",
            return_value=ps,
        ):
            rows = list(
                AuditManager(auth=move_auth, namespace=self.ns).item_timeline(
                    "moved/cfg",
                    "config",
                )
            )

        operations = {row.operation for row in rows}
        object_ids = {row.object_id for row in rows}
        self.assertIn("Update item", operations)
        self.assertIn("Move item", operations)
        self.assertIn("app/cfg", object_ids)
