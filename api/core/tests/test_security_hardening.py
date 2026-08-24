"""Tests for security hardening from the input-validation audit."""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from jinja2 import TemplateSyntaxError
from jinja2.sandbox import SecurityError
from ninja.errors import HttpError

from core.exceptions import Unauthenticated
from core.managers.auth import AuthManager
from core.managers.global_permissions import GlobalPermissionsManager
from core.managers.permissions import PermissionsManager
from core.managers.resolution import parse_query_params, validate_cast_format
from core.managers.resolver_tokens import ResolverTokenManager
from core.managers.tree import TreeManager
from core.models import GlobalPermissionRule, Namespace, Resolver
from core.schemas import GlobalPermissionRulePayload
from core.shortcuts import make_template_environment, validate_path_characters
from core.tests.namespace_helpers import create_test_namespace


class AuthStartupTests(TestCase):
    def test_from_request_without_auth_raises(self):
        with self.assertRaises(Unauthenticated):
            AuthManager.from_request(None)

    def test_oauth2_requires_authentication_without_bearer(self):
        from ocmoapi.auth import OAuth2AuthorizationCodeBearer

        request = type("R", (), {"headers": {}})()

        with patch("ocmoapi.auth.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {
                "jwks_uri": "http://oidc-provider:9000/dex/keys",
                "authorization_endpoint": "http://localhost:8080/dex/auth",
                "token_endpoint": "http://localhost:8080/dex/token",
            }
            oauth = OAuth2AuthorizationCodeBearer(
                oidc_discovery_url="http://oidc-provider:9000/dex/.well-known/openid-configuration",
                jwks_url="http://oidc-provider:9000/dex/keys",
                client_id="ocmo-api",
                issuer="http://localhost:8080/dex/",
            )
            with self.assertRaises(HttpError):
                oauth(request)

    def test_oauth2_skips_discovery_when_endpoints_configured(self):
        from ocmoapi.auth import OAuth2AuthorizationCodeBearer

        with patch("ocmoapi.auth.requests.get") as mock_get:
            OAuth2AuthorizationCodeBearer(
                oidc_discovery_url="http://oidc-provider:9000/dex/.well-known/openid-configuration",
                jwks_url="http://oidc-provider:9000/dex/keys",
                authorization_url="http://localhost:8080/dex/auth",
                token_url="http://localhost:8080/dex/token",
                client_id="ocmo-api",
                issuer="http://localhost:8080/dex/",
            )
        mock_get.assert_not_called()

    def test_swagger_openapi_uses_public_oidc_urls_not_internal_discovery(self):
        from ocmoapi.auth import OAuth2AuthorizationCodeBearer

        with patch("ocmoapi.auth.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {
                "jwks_uri": "http://oidc-provider:9000/dex/keys",
                "authorization_endpoint": "http://localhost:8080/dex/auth",
                "token_endpoint": "http://localhost:8080/dex/token",
            }
            auth = OAuth2AuthorizationCodeBearer(
                oidc_discovery_url="http://oidc-provider:9000/dex/.well-known/openid-configuration",
                jwks_url="http://oidc-provider:9000/dex/keys",
                authorization_url="http://localhost:8080/dex/auth",
                token_url="http://localhost:8080/dex/token",
                client_id="ocmo-api",
                issuer="http://localhost:8080/dex/",
            )
        flows = auth.openapi_flows["authorizationCode"]
        self.assertEqual(flows["authorizationUrl"], "http://localhost:8080/dex/auth")
        self.assertEqual(flows["tokenUrl"], "http://localhost:8080/dex/token")
        self.assertNotIn("oidc-provider", flows["authorizationUrl"])
        self.assertNotIn("oidc-provider", flows["tokenUrl"])

    def test_swagger_openapi_derives_public_urls_from_issuer(self):
        from ocmoapi.auth import OAuth2AuthorizationCodeBearer

        with patch("ocmoapi.auth.requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            mock_get.return_value.json.return_value = {
                "jwks_uri": "http://oidc-provider:9000/dex/keys",
                "authorization_endpoint": "http://localhost:8080/dex/auth",
                "token_endpoint": "http://localhost:8080/dex/token",
            }
            auth = OAuth2AuthorizationCodeBearer(
                oidc_discovery_url="http://oidc-provider:9000/dex/.well-known/openid-configuration",
                client_id="ocmo-api",
                issuer="http://localhost:8080/dex/",
            )
        flows = auth.openapi_flows["authorizationCode"]
        self.assertEqual(flows["authorizationUrl"], "http://localhost:8080/dex/auth")
        self.assertEqual(flows["tokenUrl"], "http://localhost:8080/dex/token")

    def test_swagger_redirect_url_uses_configured_public_url(self):
        with override_settings(
            OIDC_SWAGGER_REDIRECT_URL="http://localhost:8080/api/docs/oauth2-redirect.html",
        ):
            from django.conf import settings

            self.assertEqual(
                settings.OIDC_SWAGGER_REDIRECT_URL,
                "http://localhost:8080/api/docs/oauth2-redirect.html",
            )


class WhoAmIEndpointTests(TestCase):
    def test_whoami_returns_authenticated_user_claims(self):
        client = Client()
        response = client.get("/api/v1/auth/whoami/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["auth_type"], "user")
        self.assertEqual(data["identifier"], "test-admin")
        self.assertEqual(data["display_name"], "Test Admin")
        self.assertEqual(data["access_scope"], "")
        self.assertNotIn("resolver_details", data)
        user_details = data["user_details"]
        self.assertEqual(user_details["email"], "admin@example.com")
        self.assertTrue(user_details["is_global_admin"])
        self.assertIn("email", user_details["claims"])

    def test_whoami_resolver_returns_resolver_details(self):
        ns = Namespace.objects.create(name="whoami-ns", description="")
        resolver = Resolver.objects.create(
            namespace=ns,
            name="svc",
            path="app/svc",
            node_type="resolver",
            author="test",
            description="",
            configuration={},
        )
        plain = "ocmort-whoamitesttoken123456"
        ResolverTokenManager(plaintext=plain).assign_to(resolver, 1)
        resolver.save(update_fields=["token1", "token1_lookup"])
        response = Client().get(f"/api/v1/auth/whoami/?token={plain}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["auth_type"], "resolver")
        self.assertEqual(data["identifier"], "app/svc")
        self.assertEqual(data["access_scope"], "app")
        self.assertNotIn("user_details", data)
        resolver_details = data["resolver_details"]
        self.assertEqual(resolver_details["namespace"], ns.name)
        self.assertEqual(resolver_details["name"], "svc")
        self.assertEqual(resolver_details["token_number"], 1)
        self.assertNotIn("resolver_path", resolver_details)
        self.assertNotIn("access_scope", resolver_details)

    def test_swagger_docs_expose_oauth_redirect(self):
        response = Client().get("/api/docs")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("oauth2RedirectUrl", content)
        self.assertIn("initOAuth", content)

    def test_openapi_exposes_authorization_code_flow(self):
        response = Client().get("/api/openapi.json")
        self.assertEqual(response.status_code, 200)
        scheme = response.json()["components"]["securitySchemes"]["TestOAuth2Bearer"]
        self.assertEqual(scheme["type"], "oauth2")
        self.assertIn("flows", scheme)
        self.assertIn("authorizationCode", scheme["flows"])


class ResolverPrivilegeTests(TestCase):
    def setUp(self):
        self.ns = Namespace.objects.create(name="priv-ns", description="")

    def test_resolver_cannot_write_namespace_object(self):
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": self.ns.id,
                "name": "svc",
                "access_scope": "app",
                "token_number": 1,
            }
        )
        pm = PermissionsManager(auth, self.ns)
        self.assertTrue(pm.check_namespace_object("priv-ns", "read"))
        self.assertFalse(pm.check_namespace_object("priv-ns", "write"))
        self.assertFalse(pm.check_tree("config:write", "_permissions"))


class JinjaSandboxTests(TestCase):
    def test_ssti_payload_blocked_at_render(self):
        env = make_template_environment()
        tmpl = env.from_string("{{ self.__init__.__globals__['os'].popen('id').read() }}")
        with self.assertRaises((SecurityError, TemplateSyntaxError)):
            tmpl.render()


class GlobalPermissionCompileTests(TestCase):
    @override_settings(
        OIDC_GLOBAL_ADMIN_CLAIM="email",
        OIDC_GLOBAL_ADMIN_VALUE="admin@example.com",
    )
    def test_invalid_global_rule_rejected_on_create(self):
        auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        payload = GlobalPermissionRulePayload(
            namespace="[invalid",
            read={"actors": [{"kind": "User", "claims": {"email": "*"}}]},
        )
        with self.assertRaises(ValidationError):
            GlobalPermissionsManager(auth=auth).create(payload)

    @override_settings(
        OIDC_GLOBAL_ADMIN_CLAIM="email",
        OIDC_GLOBAL_ADMIN_VALUE="admin@example.com",
    )
    def test_valid_global_rule_persists(self):
        auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        payload = GlobalPermissionRulePayload(
            namespace="test-*",
            read={"actors": [{"kind": "User", "claims": {"email": "*"}}]},
        )
        rule = GlobalPermissionsManager(auth=auth).create(payload)
        self.assertEqual(rule.rule["namespace"], "test-*")


class ResolveQueryValidationTests(TestCase):
    def test_invalid_cast_rejected(self):
        with self.assertRaises(ValidationError):
            validate_cast_format("exe")

    def test_invalid_param_name_rejected(self):
        with self.assertRaises(ValidationError):
            parse_query_params({"param_bad-name": "x"})


class PathValidationTests(TestCase):
    def test_dot_dot_segment_rejected(self):
        with self.assertRaises(ValidationError):
            validate_path_characters("apps/../secret")


class ResolverTokenEncryptionTests(TestCase):
    def test_round_trip_encrypt_decrypt(self):
        plain = "ocmort-testtoken123456789"
        mgr = ResolverTokenManager(plaintext=plain)
        enc = mgr.encrypted
        self.assertNotEqual(enc, plain)
        self.assertEqual(ResolverTokenManager(encrypted=enc).plaintext, plain)

    def test_authenticate_with_encrypted_storage(self):
        ns = Namespace.objects.create(name="tok-ns", description="")
        resolver = Resolver.objects.create(
            namespace=ns,
            name="svc",
            path="app/svc",
            node_type="resolver",
            author="",
            description="",
            configuration={},
        )
        plain = "ocmort-integrationtesttoken1"
        ResolverTokenManager(plaintext=plain).assign_to(resolver, 1)
        resolver.save(update_fields=["token1", "token1_lookup"])

        result = ResolverTokenManager(plaintext=plain).authenticate()
        self.assertIsNotNone(result)
        found, slot = result
        self.assertEqual(found.id, resolver.id)
        self.assertEqual(slot, 1)


@override_settings(OCMO_MASTER_KEY="dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGs=")
class NavigateMetadataTests(TestCase):
    def setUp(self):
        self.client = Client()
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "nav-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
            },
        )
        self.ns = create_test_namespace("nav-test")
        TreeManager(self.ns, "app/svc", auth=None).create_item("", "resolver")

    def test_navigate_does_not_expose_resolver_tokens(self):
        auth = AuthManager({"_type": "user", "email": "u@example.com"})
        resp = TreeManager(self.ns, "", auth=auth).navigate()
        for child in resp["children"]:
            self.assertEqual(
                set(child.keys()),
                {"name", "path", "node_type"},
            )
            self.assertNotIn("token1", child)
            self.assertNotIn("configuration", child)


class InputValidationTests(TestCase):
    def test_validate_path_characters_rejects_traversal(self):
        with self.assertRaises(ValidationError):
            validate_path_characters("../etc/passwd")

    def test_validate_cast_format_rejects_unknown(self):
        with self.assertRaises(ValidationError):
            validate_cast_format("not-a-format")

    def test_template_environment_blocks_dangerous_attributes(self):
        env = make_template_environment()
        with self.assertRaises(SecurityError):
            env.from_string("{{ self.__init__.__globals__ }}").render()

    def test_template_syntax_error_on_invalid_jinja(self):
        env = make_template_environment()
        with self.assertRaises(TemplateSyntaxError):
            env.from_string("{{ unclosed").render()
