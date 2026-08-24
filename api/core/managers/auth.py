"""Request-scoped identity wrapper.

Wraps the parsed identity dict from request.auth and provides typed access
to user claims / resolver properties, plus per-request decision memoisation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from django.conf import settings
from django.http import HttpRequest

from ..exceptions import Unauthenticated
from .namespace import NamespaceManager
from .permissions import PermissionsManager


class AuthManager:
    """Wrap a parsed request.auth dict for type-safe identity access.

    Two identity kinds:
      User     - {"_type": "user", <OIDC_USER_*_CLAIM>: ..., ...}
      Resolver - {"_type": "resolver", "namespace": <ns_id>, "name": ...,
                  "access_scope": ..., "token_number": 1|2}

    User identity fields are read via OIDC_USER_ID_CLAIM, OIDC_USER_EMAIL_CLAIM,
    and OIDC_USER_DISPLAY_NAME_CLAIM (defaults: sub, email, name).
    """

    DEFAULT_ACTOR_IDENTITY = "Ocmo"

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw
        self._type: str = raw.get("_type", "")
        # Per-request decision memo: {key_tuple: bool}
        self._decisions: dict[tuple, bool] = {}
        self._permissions_mgr: PermissionsManager | None = None

    # ------------------------------------------------------------------
    # OIDC user-identity claim configuration (from settings)
    # ------------------------------------------------------------------

    @classmethod
    def user_id_claim(cls) -> str:
        return getattr(settings, "OIDC_USER_ID_CLAIM", "sub")

    @classmethod
    def user_email_claim(cls) -> str:
        return getattr(settings, "OIDC_USER_EMAIL_CLAIM", "email")

    @classmethod
    def user_display_name_claim(cls) -> str:
        return getattr(settings, "OIDC_USER_DISPLAY_NAME_CLAIM", "name")

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_request(cls, request: HttpRequest) -> AuthManager:
        """Build from Ninja's HttpRequest object."""
        if request is None:
            raise Unauthenticated("Authentication required")
        auth_payload = request.auth  # type: ignore[attr-defined]
        if not isinstance(auth_payload, dict):
            raise Unauthenticated("Authentication required")
        return cls(auth_payload)

    # ------------------------------------------------------------------
    # Identity type
    # ------------------------------------------------------------------

    @property
    def is_user(self) -> bool:
        return self._type == "user"

    @property
    def is_resolver(self) -> bool:
        return self._type == "resolver"

    @property
    def is_authorized(self) -> bool:
        """True when a valid auth is present (OIDC enabled and authenticated)."""
        return self._type in ("user", "resolver")

    def to_whoami(self) -> dict[str, Any]:
        """Serialize identity for GET /auth/whoami/ (validated as WhoAmISchema by Ninja)."""
        payload: dict[str, Any] = {
            "auth_type": "user" if self.is_user else "resolver",
            "identifier": self.identifier,
            "display_name": self.display_name,
            "access_scope": self.access_scope,
        }
        if self.is_user:
            payload["user_details"] = {
                "email": self.email,
                "is_global_admin": self.is_global_admin,
                "claims": self.claims,
            }
        else:
            if self.namespace_id is None:
                raise Unauthenticated("Invalid resolver identity")
            ns = NamespaceManager.get_by_pk(self.namespace_id)
            payload["resolver_details"] = {
                "namespace": ns.name,
                "name": self.resolver_name,
                "token_number": self.token_number,
            }
        return payload

    # ------------------------------------------------------------------
    # User identity
    # ------------------------------------------------------------------

    @property
    def claims(self) -> dict[str, Any]:
        """All JWT claims, excluding internal _-prefixed keys."""
        if not self.is_user:
            return {}
        return {k: v for k, v in self._raw.items() if not k.startswith("_")}

    def get_claim(self, name: str) -> Any:
        return self._raw.get(name)

    @property
    def identifier(self) -> Any:
        return self.get_claim(self.user_id_claim()) if self.is_user else self.resolver_path

    @property
    def email(self) -> Any:
        """User email from the configured OIDC claim."""
        return self.get_claim(self.user_email_claim()) if self.is_user else None

    @property
    def display_name(self) -> Any:
        return self.get_claim(self.user_display_name_claim()) if self.is_user else f"Resolver ({self.resolver_path})"

    @property
    def actor_identity(self) -> str:
        """Stable audit-trail identity for author, updater, and locked_by fields."""
        return self.display_name

    @property
    def token_number(self) -> int | None:
        if not self.is_resolver:
            return None
        return self._raw.get("token_number")

    @classmethod
    def resolve_actor_identity(cls, auth: AuthManager | None) -> str:
        """Return actor identity from auth, or the default when auth is absent."""
        if auth is None:
            return cls.DEFAULT_ACTOR_IDENTITY
        return auth.actor_identity

    @property
    def is_global_admin(self) -> bool:
        """True when the JWT satisfies OIDC_GLOBAL_ADMIN_CLAIM/VALUE."""
        if not self.is_user:
            return False
        claim_name: str = getattr(settings, "OIDC_GLOBAL_ADMIN_CLAIM", "groups")
        claim_value: str = getattr(settings, "OIDC_GLOBAL_ADMIN_VALUE", "")
        if not claim_value:
            return False
        user_val = self._raw.get(claim_name)
        if isinstance(user_val, list):
            return claim_value in user_val
        return user_val == claim_value

    # ------------------------------------------------------------------
    # Resolver identity
    # ------------------------------------------------------------------

    @property
    def namespace_id(self) -> int | None:
        return self._raw.get("namespace") if self.is_resolver else None

    @property
    def access_scope(self) -> str:
        return (self._raw.get("access_scope") or "") if self.is_resolver else ""

    @property
    def resolver_name(self) -> str | None:
        return self._raw.get("name") if self.is_resolver else None

    @property
    def resolver_path(self) -> str | None:
        """Full tree path of this resolver (<scope>/<name>)."""
        if not self.is_resolver:
            return None
        scope = self._raw.get("access_scope", "") or ""
        name = self._raw.get("name", "") or ""
        return f"{scope}/{name}" if scope else name

    # ------------------------------------------------------------------
    # Per-request decision memoisation (used by PermissionsManager)
    # ------------------------------------------------------------------

    def _get_memo(self, key: tuple) -> bool | None:
        return self._decisions.get(key)

    def _set_memo(self, key: tuple, result: bool) -> None:
        self._decisions[key] = result

    # ------------------------------------------------------------------
    # PermissionsManager lazy accessor
    # ------------------------------------------------------------------

    def permissions(self, namespace=None) -> PermissionsManager:
        """Return (lazily created) PermissionsManager for this identity.

        Re-creates the manager when a different namespace instance is supplied.
        """
        if self._permissions_mgr is None or (
            namespace is not None and self._permissions_mgr.namespace is not namespace
        ):
            self._permissions_mgr = PermissionsManager(self, namespace)
        return self._permissions_mgr

    def probe_permissions(
        self,
        operations: list[str],
        *,
        namespace_name: str | None = None,
        namespace=None,
        resource: str | None = None,
        request_ctx: dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """Batch permission probe for frontend UI gating."""
        ctx = request_ctx or {"time": datetime.now(UTC)}
        return {
            operation: self._probe_one_permission(
                operation,
                namespace_name=namespace_name,
                namespace=namespace,
                resource=resource,
                request_ctx=ctx,
            )
            for operation in operations
        }

    def _probe_one_permission(
        self,
        operation: str,
        *,
        namespace_name: str | None,
        namespace,
        resource: str | None,
        request_ctx: dict[str, Any],
    ) -> bool:
        type_, _, verb = operation.partition(":")

        if operation == "global:admin":
            return self.is_global_admin

        if operation == "namespace:create":
            return self.permissions().can_create_namespace()

        if type_ == "namespace":
            if not namespace_name:
                return False
            return self.permissions().check_namespace_object(namespace_name, verb)

        if namespace is None:
            return False

        # Lock list probes use resource="" (see LockManager.list_active).
        if type_ == "lock" and resource in (None, ""):
            return self.permissions(namespace).check_tree(operation, "", request_ctx)

        if not resource:
            return False

        return self.permissions(namespace).check_tree(operation, resource, request_ctx)
