"""PermissionsManager for Global and namespace ABAC permission checks.

Decorator API (``require_permissions``, ``PermCheck``, ``arg``) lives in
``core.decorators``.
"""

from __future__ import annotations

from ..exceptions import PermissionDenied
from ..models import Namespace
from ..utils.permissions_compiler import PermissionsCompiler
from .tree_capabilities import BUILTIN_NAMESPACE_PATHS


class PermissionsManager:
    """Evaluate Global and namespace ABAC permission checks for one identity.

    Intended lifetime: one per request, reused across multiple manager calls
    within the same request (via AuthManager.permissions()). Decision results
    are memoised on the parent AuthManager.
    """

    def __init__(self, auth, namespace=None) -> None:
        self.auth = auth
        self.namespace = namespace

    def check_namespace_object(self, namespace_name: str, op: str) -> bool:
        """Return True when the identity may perform op on namespace_name."""
        if self.auth.is_global_admin and op in ("read", "audit"):
            return True
        if self.auth.is_resolver:
            if op != "read":
                return False
            return Namespace.objects.get(id=self.auth.namespace_id).name == namespace_name

        memo_key = ("global", namespace_name, op)
        cached = self.auth._get_memo(memo_key)
        if cached is not None:
            return cached

        compiled = PermissionsCompiler.load_global_rules()

        result = False
        for rule in compiled.rules:
            if rule.matches_namespace(namespace_name.lower(), self.auth):
                if op == "read":
                    result = rule.read_actors.matches_user(self.auth) or rule.write_actors.matches_user(self.auth)
                elif op == "write":
                    result = rule.write_actors.matches_user(self.auth)
                elif op == "delete":
                    result = rule.delete_actors.matches_user(self.auth)
                elif op == "audit":
                    result = rule.audit_actors.matches_user(self.auth)
                break

        self.auth._set_memo(memo_key, result)
        return result

    def can_create_namespace(self) -> bool:
        """True when any Global Permission rule grants write to this identity."""
        if self.auth.is_resolver:
            return False
        compiled = PermissionsCompiler.load_global_rules()
        return any(rule.write_actors.matches_user(self.auth) for rule in compiled.rules)

    def require_namespace_object(self, namespace_name: str, op: str) -> None:
        """Raise PermissionDenied when check_namespace_object returns False."""
        if not self.check_namespace_object(namespace_name, op):
            raise PermissionDenied(f"Permission denied: '{op}' on namespace '{namespace_name}'")

    # ------------------------------------------------------------------
    # Namespace ABAC (in-tree operations)
    # ------------------------------------------------------------------

    def check_tree(
        self,
        action: str,
        path: str,
        request_ctx: dict | None = None,
    ) -> bool:
        """Return True when the identity may perform action on path.

        action format: "type:verb" e.g. "config:read".

        Evaluation order:
        1. Special namespace config paths → namespace:write holders.
        2. Resolver implicit scope short-circuit.
        3. Load compiled policy set.
        4. Deny policies (deny-over-allow).
        5. Allow policies.
        6. Default deny.
        """

        # Special namespace config paths — OIDC users with namespace write only
        if path in BUILTIN_NAMESPACE_PATHS:
            if self.namespace is not None and not self.auth.is_resolver:
                return self.check_namespace_object(self.namespace.name, "write")
            return False

        # Resolver implicit scope: config:resolve and secret:resolve within scope
        if self.auth.is_resolver and action in ("config:resolve", "secret:resolve"):
            scope = self.auth.access_scope
            if scope and (path == scope or path.startswith(scope + "/")):
                return True

        ns_id = self.namespace.id if self.namespace is not None else None
        memo_key = ("tree", ns_id, action, path)
        cached = self.auth._get_memo(memo_key)
        if cached is not None:
            return cached

        if self.namespace is None:
            return False

        compiled = PermissionsCompiler.load_policy_set(self.namespace)
        type_, _, verb = action.partition(":")
        verb = verb or "*"

        candidates = compiled.get_candidates(type_, verb)

        for policy in candidates.deny:
            if policy.matches(path, self.auth, request_ctx):
                self.auth._set_memo(memo_key, False)
                return False

        for policy in candidates.allow:
            if policy.matches(path, self.auth, request_ctx):
                self.auth._set_memo(memo_key, True)
                return True

        self.auth._set_memo(memo_key, False)
        return False

    def require_tree(
        self,
        action: str,
        path: str,
        request_ctx: dict | None = None,
    ) -> None:
        """Raise PermissionDenied when check_tree returns False."""
        if not self.check_tree(action, path, request_ctx):
            raise PermissionDenied(f"Permission denied: '{action}' on '{path}'")

    def require_resolve_participants(
        self,
        participants: list[dict],
        *,
        no_creds: bool = False,
    ) -> None:
        """Raise PermissionDenied when any resolve participant lacks access.

        Used on cache hits to mirror full-pipeline permission checks:
        - ``config`` → ``config:resolve``
        - ``template`` → ``config:resolve`` (same as ``load_render_template``)
        - ``secret`` → ``secret:resolve`` (skipped when ``no_creds=True``)
        """
        for participant in participants:
            kind = participant.get("kind")
            path = participant.get("path")
            if not path:
                continue
            if kind in ("config", "template"):
                self.require_tree("config:resolve", path)
            elif kind == "secret":
                if not no_creds:
                    self.require_tree("secret:resolve", path)
            else:
                raise PermissionDenied(f"Unknown resolve participant kind {kind!r} for path {path!r}")
