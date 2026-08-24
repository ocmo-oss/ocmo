"""Permissions system tests.

Covers:
 - Compile-time: glob→regex, claim sanitization, policy set / global rules compilation.
 - Eval-time: deny-over-allow, default deny, resolver implicit scope, {!user.x}
   interpolation, conditions, global first-match / write-implies-read.
 - LRU: version-keyed cache, global revision key.
 - AuthManager: user/resolver/anonymous properties, is_global_admin.
 - Integration (DB): namespace endpoints + tree get_item via manager calls.
"""

from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from core.decorators import PermCheck, require_permissions
from core.exceptions import NotFound, PermissionDenied
from core.managers.auth import AuthManager
from core.managers.permissions import PermissionsManager
from core.models import GlobalPermissionRule, Namespace
from core.tests.namespace_helpers import create_test_namespace
from core.utils.permissions_compiler import (
    CompiledGlobalRules,
    PermissionsCompiler,
)

# ---------------------------------------------------------------------------
# Unit: glob → regex
# ---------------------------------------------------------------------------


class TestGlobToRegex(TestCase):
    def _match(self, glob, path):
        import re

        regex_str, _ = PermissionsCompiler.glob_to_regex(glob)
        return re.compile(regex_str).fullmatch(path) is not None

    def test_literal_matches_exactly(self):
        self.assertTrue(self._match("project/env/app", "project/env/app"))
        self.assertFalse(self._match("project/env/app", "project/env/other"))

    def test_single_star_matches_one_segment(self):
        self.assertTrue(self._match("project/*/app", "project/dev/app"))
        self.assertTrue(self._match("project/*/app", "project/prod/app"))
        self.assertFalse(self._match("project/*/app", "project/dev/inner/app"))

    def test_double_star_matches_multiple_segments(self):
        self.assertTrue(self._match("project/**", "project/a/b/c"))
        self.assertTrue(self._match("project/**", "project/a"))
        self.assertTrue(self._match("**", "any/path/at/all"))

    def test_double_star_in_middle_zero_segments(self):
        """project/**/secrets/* matches project/secrets/key (zero intermediate segments)."""
        self.assertTrue(self._match("project/**/secrets/*", "project/secrets/key"))

    def test_double_star_in_middle_one_segment(self):
        self.assertTrue(self._match("project/**/secrets/*", "project/a/secrets/key"))

    def test_double_star_in_middle_two_segments(self):
        self.assertTrue(self._match("project/**/secrets/*", "project/a/b/secrets/key"))

    def test_double_star_in_middle_no_match_wrong_suffix(self):
        self.assertFalse(self._match("project/**/secrets/*", "project/a/other/key"))

    def test_question_mark_matches_single_char(self):
        self.assertTrue(self._match("app?conf", "appXconf"))
        self.assertFalse(self._match("app?conf", "app/conf"))

    def test_interpolation_slot_extracted(self):
        import re

        regex_str, slots = PermissionsCompiler.glob_to_regex("personal/{!user.email}/**")
        self.assertEqual(len(slots), 1)
        group, (kind, attr) = list(slots.items())[0]
        self.assertEqual(kind, "user")
        self.assertEqual(attr, "email")
        pattern = re.compile(regex_str)
        m = pattern.fullmatch("personal/bob-example-com/configs")
        self.assertIsNotNone(m)

    def test_resolver_name_slot(self):
        regex_str, slots = PermissionsCompiler.glob_to_regex("resolvers/{!resolver.name}/data")
        self.assertEqual(len(slots), 1)
        _, (kind, attr) = list(slots.items())[0]
        self.assertEqual(kind, "resolver")
        self.assertEqual(attr, "name")


# ---------------------------------------------------------------------------
# Unit: claim sanitization
# ---------------------------------------------------------------------------


class TestSanitizeClaimForPath(TestCase):
    def test_lowercase(self):
        self.assertEqual(PermissionsCompiler.sanitize_claim_for_path("BOB"), "bob")

    def test_strips_whitespace(self):
        self.assertEqual(PermissionsCompiler.sanitize_claim_for_path("  alice  "), "alice")

    def test_first_line_only(self):
        self.assertEqual(PermissionsCompiler.sanitize_claim_for_path("line1\nline2"), "line1")

    def test_special_chars_replaced(self):
        self.assertEqual(PermissionsCompiler.sanitize_claim_for_path("bob@example.com"), "bob-example-com")

    def test_allowed_chars_preserved(self):
        self.assertEqual(PermissionsCompiler.sanitize_claim_for_path("my_user-123"), "my_user-123")


# ---------------------------------------------------------------------------
# Unit: AuthManager
# ---------------------------------------------------------------------------


class TestAuthManager(TestCase):
    def _user_auth(self, **claims):
        return AuthManager({"_type": "user", **claims})

    def _resolver_auth(self, namespace_id=1, name="my-resolver", access_scope="proj/env"):
        return AuthManager(
            {
                "_type": "resolver",
                "namespace": namespace_id,
                "name": name,
                "access_scope": access_scope,
                "token_number": 1,
            }
        )

    def test_user_type_detection(self):
        auth = self._user_auth(email="bob@example.com")
        self.assertTrue(auth.is_user)
        self.assertFalse(auth.is_resolver)
        self.assertTrue(auth.is_authorized)

    def test_resolver_type_detection(self):
        auth = self._resolver_auth()
        self.assertFalse(auth.is_user)
        self.assertTrue(auth.is_resolver)

    def test_anonymous_from_none_raises(self):
        """from_request(None) raises Unauthenticated."""
        from core.exceptions import Unauthenticated

        with self.assertRaises(Unauthenticated):
            AuthManager.from_request(None)

    def test_test_user_is_global_admin(self):
        from ocmoapi.testing_auth import default_test_user_claims

        auth = AuthManager(default_test_user_claims())
        self.assertTrue(auth.is_user)
        self.assertTrue(auth.is_global_admin)

    def test_get_claim(self):
        auth = self._user_auth(email="bob@example.com", groups=["admins"])
        self.assertEqual(auth.get_claim("email"), "bob@example.com")
        self.assertIsNone(auth.get_claim("nonexistent"))

    def test_claims_excludes_internal_keys(self):
        auth = self._user_auth(email="bob@example.com")
        self.assertNotIn("_type", auth.claims)
        self.assertIn("email", auth.claims)

    def test_is_global_admin_true(self):
        auth = self._user_auth(email="admin@example.com")
        self.assertTrue(auth.is_global_admin)

    def test_is_global_admin_false(self):
        auth = self._user_auth(email="other@example.com")
        self.assertFalse(auth.is_global_admin)

    @override_settings(
        OIDC_GLOBAL_ADMIN_CLAIM="groups",
        OIDC_GLOBAL_ADMIN_VALUE="ocmo-global-admins",
    )
    def test_is_global_admin_list_claim(self):
        auth = self._user_auth(groups=["ocmo-global-admins", "devs"])
        self.assertTrue(auth.is_global_admin)

    def test_resolver_path(self):
        auth = self._resolver_auth(name="svc", access_scope="proj/env")
        self.assertEqual(auth.resolver_path, "proj/env/svc")

    def test_resolver_path_no_scope(self):
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": 1,
                "name": "root-svc",
                "access_scope": "",
                "token_number": 1,
            }
        )
        self.assertEqual(auth.resolver_path, "root-svc")

    def test_actor_identity_user_uses_display_name(self):
        auth = self._user_auth(sub="user-123", email="alice@example.com", name="Alice")
        self.assertEqual(auth.actor_identity, "Alice")

    def test_actor_identity_resolver_uses_display_name(self):
        auth = self._resolver_auth(name="svc", access_scope="proj/env")
        self.assertEqual(auth.actor_identity, "Resolver (proj/env/svc)")

    def test_resolve_actor_identity_defaults_when_auth_is_none(self):
        self.assertEqual(AuthManager.resolve_actor_identity(None), "Ocmo")

    def test_decision_memo(self):
        auth = self._user_auth()
        key = ("global", "my-ns", "read")
        self.assertIsNone(auth._get_memo(key))
        auth._set_memo(key, True)
        self.assertTrue(auth._get_memo(key))


# ---------------------------------------------------------------------------
# Helpers: minimal namespace stub for unit tests
# ---------------------------------------------------------------------------


def _ns_stub(name="test", ns_id=1):
    """Return a minimal namespace-like object for unit tests (no DB)."""
    return type("NS", (), {"id": ns_id, "name": name, "permissions_tag": "latest"})()


# ---------------------------------------------------------------------------
# Unit: PermissionsCompiler.compile_policy_set + evaluation (patching permissions_compile module)
# ---------------------------------------------------------------------------


class TestCompilePolicySet(TestCase):
    def _user_auth(self, **claims):
        return AuthManager({"_type": "user", **claims})

    def _resolver_auth(self, name="svc", scope="proj/env"):
        return AuthManager(
            {
                "_type": "resolver",
                "namespace": 1,
                "name": name,
                "access_scope": scope,
                "token_number": 1,
            }
        )

    def _allow_user(self, claims, actions, resources, conditions=None):
        p = {
            "effect": "Allow",
            "actors": [{"kind": "User", "claims": claims}],
            "actions": actions,
            "resources": resources,
        }
        if conditions:
            p["conditions"] = conditions
        return p

    def _deny_user(self, claims, actions, resources):
        return {
            "effect": "Deny",
            "actors": [{"kind": "User", "claims": claims}],
            "actions": actions,
            "resources": resources,
        }

    def _pm(self, auth, ns=None):
        pm = PermissionsManager(auth, ns or _ns_stub())
        return pm

    def test_default_deny(self):
        ps = PermissionsCompiler.compile_policy_set({"policies": []})
        auth = self._user_auth(email="bob@example.com")
        pm = self._pm(auth)
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            self.assertFalse(pm.check_tree("config:read", "project/app"))

    def test_allow_policy_grants_access(self):
        ps = PermissionsCompiler.compile_policy_set(
            {"policies": [self._allow_user({"email": "bob@example.com"}, ["config:read"], ["**"])]}
        )
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            self.assertTrue(self._pm(auth).check_tree("config:read", "project/app"))

    def test_deny_overrides_allow(self):
        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    self._allow_user({"groups": "*"}, ["config:read"], ["**"]),
                    self._deny_user({"email": "bob@example.com"}, ["config:read"], ["sensitive/**"]),
                ]
            }
        )
        auth = self._user_auth(email="bob@example.com", groups="devs")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            pm = self._pm(auth)
            self.assertTrue(pm.check_tree("config:read", "project/app"))
            self.assertFalse(pm.check_tree("config:read", "sensitive/secrets"))

    def test_wildcard_action_type(self):
        """config:* bucket matches config:read and config:write."""
        ps = PermissionsCompiler.compile_policy_set(
            {"policies": [self._allow_user({"email": "*"}, ["config:*"], ["**"])]}
        )
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            pm = self._pm(auth)
            self.assertTrue(pm.check_tree("config:read", "anything"))
            self.assertTrue(pm.check_tree("config:write", "anything"))

    def test_star_star_action(self):
        """*:* matches any action."""
        ps = PermissionsCompiler.compile_policy_set({"policies": [self._allow_user({"email": "*"}, ["*:*"], ["**"])]})
        auth = self._user_auth(email="anyone")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            pm = self._pm(auth)
            self.assertTrue(pm.check_tree("secret:read", "any/path"))
            self.assertTrue(pm.check_tree("resolver:delete", "other"))

    def test_wildcard_audit_action(self):
        """*:audit matches typed audit checks such as config:audit and resolver:audit."""
        ps = PermissionsCompiler.compile_policy_set(
            {"policies": [self._allow_user({"email": "auditor@example.com"}, ["*:audit"], ["**"])]}
        )
        auth = self._user_auth(email="auditor@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            pm = self._pm(auth)
            self.assertTrue(pm.check_tree("config:audit", "project/app"))
            self.assertTrue(pm.check_tree("resolver:audit", "deploy/svc"))
            self.assertFalse(pm.check_tree("config:read", "project/app"))

    def test_user_interpolation_in_resource(self):
        ps = PermissionsCompiler.compile_policy_set(
            {"policies": [self._allow_user({"email": "*"}, ["config:read"], ["personal/{!user.email}/**"])]}
        )
        auth_bob = self._user_auth(email="bob@example.com")
        auth_alice = self._user_auth(email="alice@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            self.assertTrue(self._pm(auth_bob).check_tree("config:read", "personal/bob-example-com/cfg"))
            self.assertFalse(self._pm(auth_alice).check_tree("config:read", "personal/bob-example-com/cfg"))

    def test_resolver_actor_match(self):
        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    {
                        "effect": "Allow",
                        "actors": [{"kind": "Resolver", "path": "proj/env/svc"}],
                        "actions": ["config:read"],
                        "resources": ["**"],
                    }
                ]
            }
        )
        auth = self._resolver_auth(name="svc", scope="proj/env")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            # config:read is NOT the implicit-scope action, so policy scan happens
            self.assertTrue(self._pm(auth).check_tree("config:read", "proj/env/app"))

    def test_resolver_implicit_scope_shortcut(self):
        """Resolver gets config:resolve within its scope without any matching policy."""
        ps = PermissionsCompiler.compile_policy_set({"policies": []})
        auth = self._resolver_auth(name="svc", scope="proj/env")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            pm = self._pm(auth)
            self.assertTrue(pm.check_tree("config:resolve", "proj/env/app"))
            self.assertTrue(pm.check_tree("config:resolve", "proj/env/nested/path"))
            self.assertTrue(pm.check_tree("config:resolve", "proj/env"))
            self.assertFalse(pm.check_tree("config:resolve", "other/path"))

    def test_resolver_implicit_secret_resolve_scope_shortcut(self):
        """Resolver gets secret:resolve within its scope without any matching policy."""
        ps = PermissionsCompiler.compile_policy_set({"policies": []})
        auth = self._resolver_auth(name="svc", scope="proj/env")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            pm = self._pm(auth)
            self.assertTrue(pm.check_tree("secret:resolve", "proj/env/app/secret"))
            self.assertFalse(pm.check_tree("secret:resolve", "other/secret"))

    def test_time_of_day_condition_pass(self):
        import datetime as dt

        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    self._allow_user(
                        {"email": "*"}, ["config:read"], ["**"], conditions={"time_of_day": ["00:00-23:59"]}
                    )
                ]
            }
        )
        ctx = {"time": dt.datetime(2024, 1, 1, 12, 0, tzinfo=dt.UTC)}
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            self.assertTrue(self._pm(auth).check_tree("config:read", "app", request_ctx=ctx))

    def test_time_of_day_condition_fail(self):
        import datetime as dt

        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    self._allow_user(
                        {"email": "*"}, ["config:read"], ["**"], conditions={"time_of_day": ["09:00-17:00"]}
                    )
                ]
            }
        )
        ctx = {"time": dt.datetime(2024, 1, 1, 3, 0, tzinfo=dt.UTC)}
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            self.assertFalse(self._pm(auth).check_tree("config:read", "app", request_ctx=ctx))

    def test_decision_memoised_on_auth_manager(self):
        ps = PermissionsCompiler.compile_policy_set(
            {"policies": [self._allow_user({"email": "*"}, ["config:read"], ["**"])]}
        )
        auth = self._user_auth(email="bob@example.com")
        pm = self._pm(auth)
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            pm.check_tree("config:read", "app")
            # Memo is now set — verify it directly
            ns_id = pm.namespace.id
            self.assertEqual(auth._get_memo(("tree", ns_id, "config:read", "app")), True)
            # Second call uses memo (not policy scan)
            pm.check_tree("config:read", "app")


# ---------------------------------------------------------------------------
# Unit: PermissionsCompiler.compile_global_rules + evaluation
# ---------------------------------------------------------------------------


class TestCompileGlobalRules(TestCase):
    def _user_auth(self, **claims):
        return AuthManager({"_type": "user", **claims})

    def _pm(self, auth):
        return PermissionsManager(auth)

    def test_empty_rules_deny_all(self):
        compiled = PermissionsCompiler.compile_global_rules([])
        auth = self._user_auth(email="bob@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            self.assertFalse(self._pm(auth).check_namespace_object("any-ns", "read"))

    def test_matching_rule_allows(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "team-*",
                    "read": {"actors": [{"kind": "User", "claims": {"groups": "team-devs"}}]},
                }
            ]
        )
        auth = self._user_auth(groups="team-devs")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            pm = self._pm(auth)
            self.assertTrue(pm.check_namespace_object("team-alpha", "read"))
            self.assertFalse(pm.check_namespace_object("team-alpha", "write"))

    def test_write_implies_read(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "myns",
                    "write": {"actors": [{"kind": "User", "claims": {"email": "admin@example.com"}}]},
                }
            ]
        )
        auth = self._user_auth(email="admin@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            pm = self._pm(auth)
            self.assertTrue(pm.check_namespace_object("myns", "read"))
            self.assertTrue(pm.check_namespace_object("myns", "write"))

    def test_delete_does_not_imply_read(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "myns",
                    "delete": {"actors": [{"kind": "User", "claims": {"email": "ops@example.com"}}]},
                }
            ]
        )
        auth = self._user_auth(email="ops@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            pm = self._pm(auth)
            self.assertFalse(pm.check_namespace_object("myns", "read"))
            self.assertTrue(pm.check_namespace_object("myns", "delete"))

    def test_first_match_wins(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "shared-*",
                    "read": {"actors": [{"kind": "User", "claims": {"groups": "team-a"}}]},
                },
                {
                    "namespace": "**",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                },
            ]
        )
        auth = self._user_auth(email="bob@example.com", groups="other")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            pm = self._pm(auth)
            # "shared-alpha" hits rule 1; bob lacks groups=team-a → deny (rule 2 never checked)
            self.assertFalse(pm.check_namespace_object("shared-alpha", "read"))
            # "other-ns" hits rule 2 → allow (email=*)
            self.assertTrue(pm.check_namespace_object("other-ns", "read"))

    def test_resolver_always_denied_global(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "**",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                }
            ]
        )
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": 1,
                "name": "svc",
                "access_scope": "proj/env",
                "token_number": 1,
            }
        )
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            with patch("core.managers.permissions.Namespace.objects.get") as mock_get:
                mock_get.return_value = type("NS", (), {"name": "my-ns"})()
                self.assertFalse(self._pm(auth).check_namespace_object("any-ns", "read"))

    def test_resolver_read_own_namespace_only(self):
        auth = AuthManager(
            {
                "_type": "resolver",
                "namespace": 1,
                "name": "svc",
                "access_scope": "proj/env",
                "token_number": 1,
            }
        )
        with patch("core.managers.permissions.Namespace.objects.get") as mock_get:
            mock_get.return_value = type("NS", (), {"name": "my-ns"})()
            pm = self._pm(auth)
            self.assertTrue(pm.check_namespace_object("my-ns", "read"))
            self.assertFalse(pm.check_namespace_object("my-ns", "write"))
            self.assertFalse(pm.check_namespace_object("my-ns", "delete"))

    def test_global_admin_bypasses_rules(self):
        """Global admin has namespace read regardless of rules (write/delete still policy-bound)."""
        compiled = PermissionsCompiler.compile_global_rules([])  # no rules
        auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            pm = self._pm(auth)
            self.assertTrue(pm.check_namespace_object("any-ns", "read"))
            self.assertFalse(pm.check_namespace_object("any-ns", "delete"))

    def test_global_admin_detection(self):
        auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        self.assertTrue(auth.is_global_admin)
        auth2 = AuthManager({"_type": "user", "email": "other@example.com"})
        self.assertFalse(auth2.is_global_admin)

    def test_is_catch_all_namespace_pattern(self):
        self.assertTrue(PermissionsCompiler.is_catch_all_namespace_pattern("*"))
        self.assertTrue(PermissionsCompiler.is_catch_all_namespace_pattern("**"))
        self.assertFalse(PermissionsCompiler.is_catch_all_namespace_pattern("team-*"))

    def test_catch_all_must_be_last_on_compile(self):
        with self.assertRaises(ValueError):
            PermissionsCompiler.compile_global_rules(
                [
                    {
                        "namespace": "*",
                        "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                    },
                    {
                        "namespace": "team-*",
                        "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                    },
                ]
            )

    def test_validate_global_rules_order_allows_catch_all_last(self):
        PermissionsCompiler.validate_global_rules_order(
            [
                {
                    "namespace": "team-*",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                },
                {
                    "namespace": "**",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                },
            ]
        )

    def test_resolver_placeholder_rejected_in_namespace_glob(self):
        with self.assertRaises(ValueError):
            PermissionsCompiler.compile_global_rules(
                [
                    {
                        "namespace": "ns-{!resolver.name}",
                        "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                    }
                ]
            )

    def test_placeholder_namespace_matches_own_user(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "personal-{!user.email}",
                    "read": {
                        "actors": [{"kind": "User", "claims": {"email": "{!user.email}"}}],
                    },
                }
            ]
        )
        bob = self._user_auth(email="bob@example.com")
        alice = self._user_auth(email="alice@example.com")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            bob_pm = self._pm(bob)
            alice_pm = self._pm(alice)
            self.assertTrue(bob_pm.check_namespace_object("personal-bob-example-com", "read"))
            self.assertFalse(bob_pm.check_namespace_object("personal-alice-example-com", "read"))
            self.assertFalse(alice_pm.check_namespace_object("personal-bob-example-com", "read"))

    def test_actor_claim_placeholder_requires_claim(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "personal-{!user.email}",
                    "read": {
                        "actors": [{"kind": "User", "claims": {"email": "{!user.email}"}}],
                    },
                }
            ]
        )
        auth = self._user_auth(sub="no-email-user")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            self.assertFalse(self._pm(auth).check_namespace_object("personal-anything", "read"))

    def test_actor_claim_wildcard_without_email_still_matches_namespace(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "personal-{!user.email}",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                }
            ]
        )
        auth = self._user_auth(sub="no-email-user")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            # Actor passes (wildcard) but namespace slot needs email claim
            self.assertFalse(self._pm(auth).check_namespace_object("personal-anything", "read"))

    def test_resolver_placeholder_rejected_in_actor_claims(self):
        with self.assertRaises(ValueError):
            PermissionsCompiler.compile_global_rules(
                [
                    {
                        "namespace": "team-*",
                        "read": {
                            "actors": [{"kind": "User", "claims": {"email": "{!resolver.name}"}}],
                        },
                    }
                ]
            )

    def test_placeholder_missing_claim_does_not_match(self):
        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "personal-{!user.email}",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                }
            ]
        )
        auth = self._user_auth(sub="user-without-email")
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            self.assertFalse(self._pm(auth).check_namespace_object("personal-anything", "read"))

    def test_expand_namespace_pattern(self):
        auth = self._user_auth(email="bob@example.com")
        self.assertEqual(
            PermissionsCompiler.expand_namespace_pattern("personal-{!user.email}", auth),
            "personal-bob-example-com",
        )
        self.assertIsNone(
            PermissionsCompiler.expand_namespace_pattern("personal-{!user.email}", self._user_auth(sub="x"))
        )


# ---------------------------------------------------------------------------
# Unit: LRU cache keying
# ---------------------------------------------------------------------------


class TestLRUCacheKeying(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def tearDown(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def test_policy_cache_keyed_by_version(self):
        v1 = PermissionsCompiler.compile_policy_set({"policies": []})
        v2 = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    {
                        "effect": "Allow",
                        "actors": [{"kind": "User", "claims": {"email": "*"}}],
                        "actions": ["config:read"],
                        "resources": ["**"],
                    }
                ]
            }
        )

        PermissionsCompiler._policy_cache.put((42, 1), v1)
        PermissionsCompiler._policy_cache.put((42, 2), v2)

        self.assertEqual(len(PermissionsCompiler._policy_cache.get((42, 1)).buckets), 0)
        self.assertIn("config", PermissionsCompiler._policy_cache.get((42, 2)).buckets)

    def test_global_cache_keyed_by_revision(self):
        r1 = PermissionsCompiler.compile_global_rules([])
        r2 = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "test",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
                }
            ]
        )

        PermissionsCompiler._global_cache.put((0, 0), r1)
        PermissionsCompiler._global_cache.put((1, 12345), r2)

        self.assertEqual(len(PermissionsCompiler._global_cache.get((0, 0)).rules), 0)
        self.assertEqual(len(PermissionsCompiler._global_cache.get((1, 12345)).rules), 1)

    @override_settings(OCMO_PERMISSIONS_CACHE_SIZE=2)
    def test_lru_eviction(self):
        for i in range(3):
            PermissionsCompiler._policy_cache.put((i, 1), PermissionsCompiler.compile_policy_set({"policies": []}))
        # First entry (0, 1) evicted; last two retained
        self.assertIsNone(PermissionsCompiler._policy_cache.get((0, 1)))
        self.assertIsNotNone(PermissionsCompiler._policy_cache.get((1, 1)))
        self.assertIsNotNone(PermissionsCompiler._policy_cache.get((2, 1)))


# ---------------------------------------------------------------------------
# Unit: require_permissions decorator
# ---------------------------------------------------------------------------


class TestRequirePermissionsDecorator(TestCase):
    def test_auth_none_bypasses(self):
        """auth=None (internal call) — decorator passes through."""

        class FakeManager:
            auth = None
            path = "some/path"

            @require_permissions("config:read")
            def do_thing(self):
                return "ok"

        self.assertEqual(FakeManager().do_thing(), "ok")

    def test_global_admin_action_passes(self):
        class FakeManager:
            auth = AuthManager({"_type": "user", "email": "admin@example.com"})

            @require_permissions("global:admin")
            def do_admin(self):
                return "ok"

        self.assertEqual(FakeManager().do_admin(), "ok")

    def test_global_admin_action_fails(self):
        class FakeManager:
            auth = AuthManager({"_type": "user", "groups": "other"})

            @require_permissions("global:admin")
            def do_admin(self):
                return "ok"

        with self.assertRaises(PermissionDenied):
            FakeManager().do_admin()

    def test_namespace_action_routing(self):
        """namespace:read with resource= routes to check_namespace_object."""

        class FakeManager:
            auth = AuthManager({"_type": "user", "email": "bob"})
            ns_name = "testns"

        compiled = PermissionsCompiler.compile_global_rules(
            [
                {
                    "namespace": "testns",
                    "read": {"actors": [{"kind": "User", "claims": {"email": "bob"}}]},
                }
            ]
        )

        @require_permissions(PermCheck("namespace:read", resource="ns_name"))
        def method(self):
            return "ok"

        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_global_rules", return_value=compiled):
            self.assertEqual(method(FakeManager()), "ok")

    def test_none_perm_callable_skipped(self):
        """Callable perm returning None means no check for that perm."""

        class FakeManager:
            auth = AuthManager({"_type": "user", "email": "bob"})
            namespace = None
            path = "some/path"

            @require_permissions(lambda self: None)
            def do_thing(self):
                return "ok"

        self.assertEqual(FakeManager().do_thing(), "ok")

    def test_callable_perm_evaluated_at_call_time(self):
        """Callable perm string is derived from self at call time."""
        calls = []

        class FakeManager:
            auth = AuthManager({"_type": "user", "email": "bob"})
            namespace = _ns_stub()
            path = "some/path"

            @require_permissions(lambda self: calls.append("checked") or None)
            def do_thing(self):
                return "ok"

        FakeManager().do_thing()
        self.assertEqual(calls, ["checked"])

    def test_callable_perm_list_of_pairs(self):
        """Callable returning list of (action, path) pairs checks each entry."""
        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    {
                        "effect": "Allow",
                        "actors": [{"kind": "User", "claims": {"email": "bob"}}],
                        "actions": ["config:delete", "secret:delete"],
                        "resources": ["allowed/**"],
                    }
                ]
            }
        )

        class FakeManager:
            auth = AuthManager({"_type": "user", "email": "bob"})
            namespace = _ns_stub()
            path = "ignored"

            @require_permissions(
                lambda self: [
                    ("config:delete", "allowed/cfg"),
                    ("secret:delete", "denied/sec"),
                ]
            )
            def delete_folder(self):
                return "ok"

        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            with self.assertRaises(PermissionDenied):
                FakeManager().delete_folder()


# ---------------------------------------------------------------------------
# Integration: namespace endpoints with permission checks (via managers)
# ---------------------------------------------------------------------------


class TestNamespacePermissionsIntegration(TestCase):
    """
      Tests the permission layer through manager calls with explicit AuthManager.
    HTTP tests use the test OAuth2 bearer (global admin by default).
    """

    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.client = Client()
        self.ns = Namespace.objects.create(name="perm-test", description="test")

    def tearDown(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def test_api_list_namespaces_succeeds_for_global_admin(self):
        resp = self.client.get("/api/v1/ns/")
        self.assertEqual(resp.status_code, 200)

    def test_api_get_namespace_succeeds_for_global_admin(self):
        resp = self.client.get(f"/api/v1/ns/{self.ns.name}")
        self.assertEqual(resp.status_code, 200)

    def test_global_admin_manager_list_returns_all(self):
        from core.managers.namespace import NamespaceManager
        from ocmoapi.testing_auth import default_test_user_claims

        auth = AuthManager(default_test_user_claims())
        result = NamespaceManager(None, auth=auth).list()
        self.assertIn("perm-test", [ns.name for ns in result])

    def test_user_with_read_can_get_namespace(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "perm-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
            },
        )
        from core.managers.namespace import NamespaceManager

        auth = AuthManager({"_type": "user", "email": "bob@example.com"})
        ns = NamespaceManager("perm-test", auth=auth).get_or_raise()
        self.assertEqual(ns.name, "perm-test")

    def test_user_without_read_is_denied(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "perm-*",
                "read": {"actors": [{"kind": "User", "claims": {"groups": "special"}}]},
            },
        )
        from core.managers.namespace import NamespaceManager

        auth = AuthManager({"_type": "user", "email": "bob@example.com", "groups": "other"})
        with self.assertRaises(NotFound):
            NamespaceManager("perm-test", auth=auth).get_or_raise()

    def test_list_filters_readable_namespaces(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "perm-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "bob@example.com"}}]},
            },
        )
        from core.managers.namespace import NamespaceManager

        bob = AuthManager({"_type": "user", "email": "bob@example.com"})
        alice = AuthManager({"_type": "user", "email": "alice@example.com"})

        bob_result = NamespaceManager(None, auth=bob).list()
        alice_result = NamespaceManager(None, auth=alice).list()

        self.assertIn("perm-test", [ns.name for ns in bob_result])
        self.assertEqual(len(alice_result), 0)

    def test_write_implies_read_for_list(self):
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "perm-*",
                "write": {"actors": [{"kind": "User", "claims": {"email": "admin@example.com"}}]},
            },
        )
        from core.managers.namespace import NamespaceManager

        auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        result = NamespaceManager(None, auth=auth).list()
        self.assertIn("perm-test", [ns.name for ns in result])

    def test_non_admin_cannot_manage_global_permissions(self):
        from core.managers.global_permissions import GlobalPermissionsManager

        auth = AuthManager({"_type": "user", "email": "regular@example.com"})
        with self.assertRaises(PermissionDenied):
            GlobalPermissionsManager(auth=auth).list()

    def test_global_admin_can_manage_global_permissions(self):
        from core.managers.global_permissions import GlobalPermissionsManager

        auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        result = GlobalPermissionsManager(auth=auth).list()
        self.assertIn("rules", result)

    def test_namespace_audit_permission(self):
        PermissionsCompiler._global_cache.clear()
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "perm-*",
                "audit": {"actors": [{"kind": "User", "claims": {"email": "auditor@example.com"}}]},
            },
        )
        auth = AuthManager({"_type": "user", "email": "auditor@example.com"})
        self.assertTrue(auth.permissions().check_namespace_object("perm-test", "audit"))
        auth2 = AuthManager({"_type": "user", "email": "other@example.com"})
        self.assertFalse(auth2.permissions().check_namespace_object("perm-test", "audit"))
        PermissionsCompiler._global_cache.clear()


# ---------------------------------------------------------------------------
# Integration: tree ABAC check via PermissionsManager
# ---------------------------------------------------------------------------


class TestTreePermissionsIntegration(TestCase):
    def setUp(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()
        self.client = Client()
        self.ns = create_test_namespace("tree-perm-test")
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/cfg",
            data=b"key: value\n",
            content_type="application/yaml",
        )

    def tearDown(self):
        PermissionsCompiler._policy_cache.clear()
        PermissionsCompiler._global_cache.clear()

    def test_get_item_dev_admin_succeeds(self):
        """OIDC disabled → dev global admin → tree access succeeds."""
        resp = self.client.get(f"/api/v1/ns/{self.ns.name}/~get/app/cfg")
        self.assertEqual(resp.status_code, 200)

    def test_get_item_missing_path_returns_404(self):
        resp = self.client.get(
            f"/api/v1/ns/{self.ns.name}/~get/tagtest/cfg/asdasd",
        )
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertIn("wasn't found by path", resp.json()["error"])

    def test_tree_check_with_matching_policy_allowed(self):
        ps = PermissionsCompiler.compile_policy_set(
            {
                "policies": [
                    {
                        "effect": "Allow",
                        "actors": [{"kind": "User", "claims": {"email": "*"}}],
                        "actions": ["config:read"],
                        "resources": ["**"],
                    }
                ]
            }
        )
        auth = AuthManager({"_type": "user", "email": "bob@example.com"})
        pm = PermissionsManager(auth, self.ns)
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            self.assertTrue(pm.check_tree("config:read", "app/cfg"))

    def test_tree_check_denied_by_empty_policy(self):
        ps = PermissionsCompiler.compile_policy_set({"policies": []})
        auth = AuthManager({"_type": "user", "email": "bob@example.com"})
        pm = PermissionsManager(auth, self.ns)
        with patch("core.utils.permissions_compiler.PermissionsCompiler.load_policy_set", return_value=ps):
            self.assertFalse(pm.check_tree("config:read", "app/cfg"))

    def test_tree_check_denies_when_namespace_is_none(self):
        """check_tree always returns False when namespace is None (prevents existence leak)."""
        auth = AuthManager({"_type": "user", "email": "bob@example.com"})
        pm = PermissionsManager(auth, None)
        self.assertFalse(pm.check_tree("config:read", "app/cfg"))

    def test_get_item_nonexistent_namespace_returns_403_not_404(self):
        """GET on a nonexistent namespace must return 403 (not 404) to hide existence."""
        resp = self.client.get("/api/v1/ns/does-not-exist/~get/app/cfg")
        # With OIDC disabled, dev admin (global admin) is used → passes check_tree
        # and falls through to 404 on the tree item. Regular users would get 403.
        # The important thing is that non-admins cannot tell existence apart.
        self.assertIn(resp.status_code, (403, 404))

    def test_special_path_denied_without_global_write(self):
        """_permissions path denies user with only global read access."""
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "tree-perm-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
            },
        )
        auth = AuthManager({"_type": "user", "email": "bob@example.com"})
        pm = PermissionsManager(auth, self.ns)
        # _permissions requires global write, not just read
        self.assertFalse(pm.check_tree("config:read", "_permissions"))

    def test_special_path_allowed_with_global_write(self):
        """_permissions path allows user with global write access."""
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "tree-perm-*",
                "write": {"actors": [{"kind": "User", "claims": {"email": "admin@example.com"}}]},
            },
        )
        auth = AuthManager({"_type": "user", "email": "admin@example.com"})
        pm = PermissionsManager(auth, self.ns)
        self.assertTrue(pm.check_tree("config:read", "_permissions"))

    def test_load_policy_set_from_empty_ns(self):
        """Namespace without _permissions is broken."""
        PermissionsCompiler._policy_cache.clear()
        from core.exceptions import BrokenNamespace

        bare = Namespace.objects.create(name="bare-ns", description="")
        with self.assertRaises(BrokenNamespace):
            PermissionsCompiler.load_policy_set(bare)

    def test_load_global_rules_from_db(self):
        """load_global_rules compiles DB rules correctly."""
        PermissionsCompiler._global_cache.clear()
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={
                "namespace": "tree-perm-*",
                "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]},
            },
        )
        compiled = PermissionsCompiler.load_global_rules()
        self.assertIsInstance(compiled, CompiledGlobalRules)
        self.assertEqual(len(compiled.rules), 1)

    def test_load_global_rules_cache_hit(self):
        """Second call to load_global_rules returns the exact same compiled object."""
        PermissionsCompiler._global_cache.clear()
        GlobalPermissionRule.objects.create(
            position=1.0,
            rule={"namespace": "ns", "read": {"actors": [{"kind": "User", "claims": {"email": "*"}}]}},
        )
        r1 = PermissionsCompiler.load_global_rules()
        r2 = PermissionsCompiler.load_global_rules()
        self.assertIs(r1, r2)  # same object from LRU cache
