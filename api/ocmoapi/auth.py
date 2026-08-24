import json
from typing import Any

import jwt
import requests
from django.conf import settings as django_settings
from django.shortcuts import render
from django.utils import timezone
from jwt import PyJWKClient
from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja.openapi.docs import HttpRequest, HttpResponse, Swagger, _csrf_needed
from ninja.security.apikey import APIKeyBase
from ninja.security.base import AuthBase, SecuritySchema
from ninja.types import DictStrAny

from core.managers.resolver_tokens import ResolverTokenManager


class OAuth2AuthorizationCodeBearer(AuthBase):
    openapi_type = "oauth2"

    def __init__(
        self,
        oidc_discovery_url: str,
        client_id: str,
        issuer: str,
        jwks_url: str | None = None,
        authorization_url: str | None = None,
        token_url: str | None = None,
    ) -> None:
        self.client_id = client_id
        self.issuer = issuer
        issuer_base = issuer.rstrip("/")
        self.authorization_url = authorization_url or f"{issuer_base}/auth"
        self.token_url = token_url or f"{issuer_base}/token"
        self.jwks_url = jwks_url
        self.jwks_client: PyJWKClient | None = None

        if jwks_url and authorization_url and token_url:
            # Static OIDC endpoints (compose / offline OpenAPI export) — no discovery fetch.
            pass
        else:
            resp = requests.get(oidc_discovery_url)
            resp.raise_for_status()
            well_known_manifest = resp.json()
            try:
                self.jwks_url = jwks_url or well_known_manifest["jwks_uri"]
                self.authorization_url = authorization_url or well_known_manifest["authorization_endpoint"]
                self.token_url = token_url or well_known_manifest["token_endpoint"]
            except KeyError as e:
                raise ValueError(
                    f"OIDC discovery document by URL {oidc_discovery_url} doesn't contain required key: {e}"
                ) from e
        self.openapi_flows = {
            "authorizationCode": {
                "scopes": {"openid": "", "profile": "", "email": "", "groups": ""},
                "authorizationUrl": self.authorization_url,
                "tokenUrl": self.token_url,
            }
        }

        super().__init__()

    @property
    def openapi_security_schema(self) -> SecuritySchema:
        flows = getattr(self, "openapi_flows", None)
        if flows:
            return SecuritySchema(type="oauth2", flows=flows)
        return SecuritySchema(type="http", scheme="bearer", bearerFormat="JWT")

    @openapi_security_schema.setter
    def openapi_security_schema(self, value: SecuritySchema) -> None:
        return

    def __call__(self, request: HttpRequest) -> Any | None:
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HttpError(403, "Not authenticated")

        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HttpError(403, "Not authenticated")

        token = parts[1]

        try:
            if self.jwks_client is None:
                if not self.jwks_url:
                    raise HttpError(401, "Invalid token: JWKS URL is not configured")
                self.jwks_client = PyJWKClient(self.jwks_url)
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            token_info = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=getattr(django_settings, "OIDC_JWT_AUDIENCES", [self.client_id]),
                issuer=self.issuer,
            )
        except Exception as e:
            raise HttpError(401, f"Invalid token: {e}") from e

        return self.authenticate(request, token_info)

    def authenticate(self, request: HttpRequest, token_info: dict) -> Any | None:
        technical_claims = ("exp", "jti", "aud", "iat", "at_hash", "nbf", "typ", "c_hash")
        oauth2_claims = {k: v for k, v in token_info.items() if k not in technical_claims}
        oauth2_claims["_type"] = "user"
        return oauth2_claims


class SwaggerOAuth2(Swagger):
    def __init__(self, settings: DictStrAny | None = None, auth: DictStrAny | None = None):
        self.auth = auth
        super().__init__(settings)

    def render_page(self, request: HttpRequest, api: "NinjaAPI", **kwargs: Any) -> HttpResponse:
        self.settings["url"] = self.get_openapi_url(api, kwargs)

        context = {
            "swagger_settings": json.dumps(self.settings, indent=1),
            "api": api,
            "add_csrf": _csrf_needed(api),
            "add_auth": bool(self.auth),
            "oauth2_redirect_url": django_settings.OIDC_SWAGGER_REDIRECT_URL,
            "swagger_auth": json.dumps(self.auth, indent=1),
        }
        return render(request, self.template, context)


RESOLVER_TOKEN_QUERY_PARAM = "token"
RESOLVER_TOKEN_HEADER = "X-Ocmo-Resolver-Token"


class ResolverAuth(APIKeyBase):
    openapi_in = "query"
    param_name = RESOLVER_TOKEN_QUERY_PARAM

    def _get_key(self, request):
        return request.GET.get(RESOLVER_TOKEN_QUERY_PARAM) or request.headers.get(RESOLVER_TOKEN_HEADER)

    def authenticate(self, request, key):
        if key is None:
            return None
        result = ResolverTokenManager(plaintext=key).authenticate()
        if result is None:
            return None
        resolver, token_number = result
        if token_number == 1:
            resolver.token1_last_used = timezone.now()
        else:
            resolver.token2_last_used = timezone.now()
        resolver.save(update_fields=[f"token{token_number}_last_used"])
        return {
            "_type": "resolver",
            "namespace": resolver.namespace_id,
            "name": resolver.name,
            "access_scope": "/".join(resolver.path.split("/")[:-1]),
            "token_number": token_number,
        }


resolver_auth = ResolverAuth()
