"""Tests for multi-audience JWT validation settings."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from ocmoapi.auth import OAuth2AuthorizationCodeBearer


class OIDCJWTAudiencesSettingsTest(SimpleTestCase):
    def test_default_audiences_include_api_and_sdk(self):
        from django.conf import settings

        self.assertIn("ocmo-api", settings.OIDC_JWT_AUDIENCES)
        self.assertIn("ocmo-sdk", settings.OIDC_JWT_AUDIENCES)

    @override_settings(OIDC_JWT_AUDIENCES=["custom-aud"])
    def test_custom_audiences_override(self):
        from django.conf import settings

        self.assertEqual(settings.OIDC_JWT_AUDIENCES, ["custom-aud"])


class OAuth2AuthorizationCodeBearerAudienceTest(SimpleTestCase):
    @patch("ocmoapi.auth.requests.get")
    @patch("ocmoapi.auth.PyJWKClient")
    @patch("ocmoapi.auth.jwt.decode")
    def test_jwt_decode_uses_configured_audiences(
        self,
        mock_decode: MagicMock,
        mock_jwks_client_cls: MagicMock,
        mock_requests_get: MagicMock,
    ) -> None:
        mock_requests_get.return_value.json.return_value = {
            "jwks_uri": "https://idp/keys",
            "authorization_endpoint": "https://idp/auth",
            "token_endpoint": "https://idp/token",
        }
        mock_requests_get.return_value.raise_for_status = MagicMock()

        signing_key = MagicMock()
        signing_key.key = "public-key"
        mock_jwks_client_cls.return_value.get_signing_key_from_jwt.return_value = signing_key
        mock_decode.return_value = {"sub": "svc", "aud": "ocmo-sdk"}

        auth = OAuth2AuthorizationCodeBearer(
            oidc_discovery_url="https://idp/.well-known/openid-configuration",
            client_id="ocmo-api",
            issuer="https://idp/",
            jwks_url="https://idp/keys",
            authorization_url="https://idp/auth",
            token_url="https://idp/token",
        )

        request = MagicMock()
        request.headers = {"Authorization": "Bearer token-value"}

        with override_settings(OIDC_JWT_AUDIENCES=["ocmo-api", "ocmo-sdk"]):
            result = auth(request)

        mock_decode.assert_called_once()
        _, kwargs = mock_decode.call_args
        self.assertEqual(kwargs["audience"], ["ocmo-api", "ocmo-sdk"])
        self.assertEqual(result["sub"], "svc")
