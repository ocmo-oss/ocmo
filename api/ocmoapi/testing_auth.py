"""Synthetic OAuth2 bearer for the Django test runner — not used in production."""

from __future__ import annotations

from typing import Any

from django.conf import settings as django_settings
from ninja.errors import HttpError
from ninja.openapi.docs import HttpRequest
from ninja.security.base import AuthBase, SecuritySchema

_test_auth_deny = False
_test_auth_user: dict[str, Any] | None = None


def default_test_user_claims() -> dict[str, Any]:
    email_claim = django_settings.OIDC_USER_EMAIL_CLAIM
    display_claim = django_settings.OIDC_USER_DISPLAY_NAME_CLAIM
    admin_claim = django_settings.OIDC_GLOBAL_ADMIN_CLAIM
    admin_value = django_settings.OIDC_GLOBAL_ADMIN_VALUE
    claims: dict[str, Any] = {
        "_type": "user",
        django_settings.OIDC_USER_ID_CLAIM: "test-admin",
        email_claim: admin_value if admin_claim == email_claim else "admin@example.com",
        display_claim: "Test Admin",
    }
    if admin_value:
        claims[admin_claim] = admin_value
    return claims


class TestOAuth2Bearer(AuthBase):
    openapi_type = "oauth2"
    openapi_flows = {
        "authorizationCode": {
            "scopes": {"openid": "", "profile": "", "email": "", "groups": ""},
            "authorizationUrl": "http://localhost/dex/auth",
            "tokenUrl": "http://localhost/dex/token",
        }
    }

    @property
    def openapi_security_schema(self) -> SecuritySchema:
        return SecuritySchema(type="oauth2", flows=self.openapi_flows)

    @openapi_security_schema.setter
    def openapi_security_schema(self, value: SecuritySchema) -> None:
        return

    def __call__(self, request: HttpRequest) -> Any | None:
        if _test_auth_deny:
            raise HttpError(403, "Not authenticated")

        if _test_auth_user is not None:
            return dict(_test_auth_user)

        authorization = request.headers.get("Authorization")
        if not authorization:
            return default_test_user_claims()

        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HttpError(403, "Not authenticated")
        return default_test_user_claims()
