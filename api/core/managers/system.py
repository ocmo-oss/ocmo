"""Operational metadata exposed by unauthenticated system endpoints."""

from __future__ import annotations

from django.conf import settings

from ..managers.tree_capabilities import (
    builtin_namespace_paths_payload,
    reserved_tags_payload,
)
from ..notice import LICENSE_NAME, LICENSE_SPDX, load_notice_text
from ..version import PRODUCT, VERSION


class SystemManager:
    """Build payloads for `/api/version` and related probes."""

    def version_payload(self, *, include_notice: bool = False) -> dict:
        payload = {
            "product": PRODUCT,
            "version": VERSION,
            "license": LICENSE_SPDX,
            "license_name": LICENSE_NAME,
            "config_metadata_key": settings.OCMO_CONFIG_METADATA_KEY,
            "builtin_namespace_paths": builtin_namespace_paths_payload(),
            "reserved_tags": reserved_tags_payload(),
            "auth": self.public_auth(),
        }
        if include_notice:
            payload["notice"] = load_notice_text()
        return payload

    def public_auth(self) -> dict:
        # SPA OIDC client expects authority without a trailing slash (discovery URL construction).
        issuer = settings.OIDC_ISSUER.rstrip("/")
        return {
            "oidc": {
                "issuer": issuer,
                "client_id": settings.OIDC_CLIENT_ID,
                "authorization_url": settings.OIDC_AUTHORIZATION_URL,
                "token_url": settings.OIDC_TOKEN_URL,
                "scopes": settings.OIDC_SCOPES,
            },
        }
