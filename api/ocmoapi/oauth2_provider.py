"""OAuth2 bearer singleton wired for production or the Django test runner."""

from typing import Any

from django.conf import settings as django_settings

from . import settings
from .auth import OAuth2AuthorizationCodeBearer

oauth2_auth: Any
if django_settings.TESTING:
    from .testing_auth import TestOAuth2Bearer

    oauth2_auth = TestOAuth2Bearer()
else:
    oauth2_auth = OAuth2AuthorizationCodeBearer(
        oidc_discovery_url=settings.OIDC_DISCOVERY_DOCUMENT_URL,
        jwks_url=settings.OIDC_JWKS_URL,
        authorization_url=settings.OIDC_AUTHORIZATION_URL,
        token_url=settings.OIDC_TOKEN_URL,
        client_id=settings.OIDC_CLIENT_ID,
        issuer=settings.OIDC_ISSUER,
    )
