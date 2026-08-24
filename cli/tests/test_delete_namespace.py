"""Tests for delete namespace command output."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from ocmo._bridge import _normalize_no_content_response
from ocmo._generated.api.namespace.delete_namespace import _parse_response
from ocmo._generated.models.namespace_deleted_schema import NamespaceDeletedSchema

from ocmo_cli.commands.generated import _execute_generated


def test_delete_namespace_empty_204_parses_confirmation() -> None:
    request = httpx.Request("DELETE", "https://ocmo.example.com/api/v1/ns/my-pre-last-ns")
    response = httpx.Response(204, request=request)

    normalized = _normalize_no_content_response(response)
    parsed = _parse_response(client=object(), response=normalized)

    assert isinstance(parsed, NamespaceDeletedSchema)
    assert parsed.namespace == "my-pre-last-ns"


def test_execute_generated_delete_namespace_emits_result(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = MagicMock()
    ctx.output = None
    ctx.dry_run = False
    ctx.yes = True
    ctx.no_color = True
    client = MagicMock()
    ctx.client.return_value = client
    client.delete_namespace.return_value = NamespaceDeletedSchema(
        namespace="my-pre-last-ns",
        success=True,
    )

    _execute_generated(
        ctx=ctx,
        op_ids=["delete_namespace"],
        action="delete",
        resource="namespace",
        address="my-pre-last-ns",
        namespace=None,
        output_fmt="name",
        field=None,
        version_flag=None,
        dry_run=False,
        yes=True,
        file_path=None,
        confirm_mode="destructive",
    )

    captured = capsys.readouterr()
    assert captured.out == "my-pre-last-ns\n"
    assert captured.err == ""
