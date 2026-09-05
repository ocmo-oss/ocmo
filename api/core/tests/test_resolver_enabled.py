"""Tests for resolver enable/disable."""

import json

from django.test import Client, TestCase

from core.managers.resolver_tokens import ResolverTokenManager
from core.managers.tree import TreeManager
from core.models import Resolver
from core.tests.namespace_helpers import create_test_namespace


class ResolverEnabledManagerTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("resolver-enabled-ns")
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: value\n", "config")

    def _create_resolver(self, path: str = "app/svc") -> tuple[Resolver, str]:
        TreeManager(self.ns, path, auth=None).create_item("{}", "resolver")
        resolver = Resolver.objects.get(namespace=self.ns, path=path)
        plain = "ocmort-resolverenabledtesttoken1"
        ResolverTokenManager(plaintext=plain).assign_to(resolver, 1)
        resolver.save(update_fields=["token1", "token1_lookup"])
        return resolver, plain

    def test_new_resolver_is_enabled_by_default(self):
        resolver, _ = self._create_resolver()
        self.assertTrue(resolver.enabled)

    def test_set_resolver_enabled_is_idempotent(self):
        TreeManager(self.ns, "app/svc", auth=None).create_item("{}", "resolver")
        mgr = TreeManager(self.ns, "app/svc", auth=None)

        first = mgr.set_resolver_enabled(False)
        self.assertFalse(first.enabled)

        second = mgr.set_resolver_enabled(False)
        self.assertFalse(second.enabled)

        enabled = mgr.set_resolver_enabled(True)
        self.assertTrue(enabled.enabled)


class ResolverEnabledAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("resolver-enabled-auth-ns")
        TreeManager(self.ns, "app/cfg", auth=None).create_item("key: value\n", "config")
        self.resolver = Resolver.objects.create(
            namespace=self.ns,
            name="svc",
            path="app/svc",
            node_type="resolver",
            author="test",
            description="",
            configuration={},
            enabled=False,
        )
        self.plain = "ocmort-disabledresolverauthtoken"
        ResolverTokenManager(plaintext=self.plain).assign_to(self.resolver, 1)
        self.resolver.save(update_fields=["token1", "token1_lookup"])

    def test_disabled_resolver_whoami_returns_enabled_false(self):
        response = self.client.get(f"/api/v1/auth/whoami/?token={self.plain}")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["auth_type"], "resolver")
        self.assertFalse(data["resolver_details"]["enabled"])

    def test_disabled_resolver_can_i_is_forbidden(self):
        response = self.client.post(
            f"/api/v1/auth/can-i/?token={self.plain}",
            data=json.dumps({"operations": ["config:resolve"], "namespace": self.ns.name, "resource": "app/cfg"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403, response.content)

    def test_disabled_resolver_resolve_is_forbidden(self):
        response = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~resolve/cfg?token={self.plain}",
        )
        self.assertEqual(response.status_code, 403, response.content)

    def test_disabled_resolver_resolve_parameters_is_forbidden(self):
        response = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~resolve-parameters/cfg?token={self.plain}",
        )
        self.assertEqual(response.status_code, 403, response.content)

    def test_enabled_resolver_can_resolve(self):
        self.resolver.enabled = True
        self.resolver.save(update_fields=["enabled"])
        response = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~resolve/cfg?token={self.plain}",
        )
        self.assertEqual(response.status_code, 200, response.content)


class ResolverEnabledApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ns = create_test_namespace("resolver-enabled-api-ns")
        TreeManager(self.ns, "app/svc", auth=None).create_item("{}", "resolver")

    def test_set_enabled_endpoint_updates_resolver(self):
        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~resolver/~disable/app/svc",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertFalse(data["enabled"])

        resolver = Resolver.objects.get(namespace=self.ns, path="app/svc")
        self.assertFalse(resolver.enabled)

        response = self.client.post(
            f"/api/v1/ns/{self.ns.name}/~resolver/~enable/app/svc",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["enabled"])

    def test_get_resolver_includes_enabled(self):
        resolver = Resolver.objects.get(namespace=self.ns, path="app/svc")
        resolver.enabled = False
        resolver.save(update_fields=["enabled"])

        response = self.client.get(f"/api/v1/ns/{self.ns.name}/~get/app/svc")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["enabled"])
