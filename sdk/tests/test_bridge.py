"""Tests for generated-client response normalization."""

from __future__ import annotations

import httpx

from ocmo._bridge import _normalize_no_content_response
from ocmo._generated.api.namespace.delete_namespace import _parse_response
from ocmo._generated.models.namespace_deleted_schema import NamespaceDeletedSchema


def test_normalize_empty_204_delete_namespace_synthesizes_payload() -> None:
    request = httpx.Request("DELETE", "https://ocmo.example.com/api/v1/ns/my-pre-last-ns")
    response = httpx.Response(204, request=request)

    normalized = _normalize_no_content_response(response)
    parsed = _parse_response(client=object(), response=normalized)

    assert isinstance(parsed, NamespaceDeletedSchema)
    assert parsed.namespace == "my-pre-last-ns"
    assert parsed.success is True


def test_normalize_empty_204_other_delete_keeps_info_schema_body() -> None:
    request = httpx.Request("DELETE", "https://ocmo.example.com/api/v1/global-permissions/rule-1")
    response = httpx.Response(204, request=request)

    normalized = _normalize_no_content_response(response)

    assert normalized.json() == {"details": ""}
