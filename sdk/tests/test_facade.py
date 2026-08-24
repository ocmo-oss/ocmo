"""Tests for generated-operation facade on OcmoClient / NamespaceView."""

import httpx
import pytest

from ocmo.client import OcmoClient
from ocmo.config import OcmoConfig
from ocmo.errors import OcmoNotFoundError

_SERVER = "https://ocmo.example.com"


def _config(**kwargs) -> OcmoConfig:
    return OcmoConfig(server=_SERVER, **kwargs)


def test_client_exposes_whoami(respx_mock):
    respx_mock.get(f"{_SERVER}/api/v1/auth/whoami/").mock(
        return_value=httpx.Response(
            200,
            json={
                "auth_type": "user",
                "identifier": "sub-123",
                "display_name": "Test User",
                "user_details": {
                    "is_global_admin": False,
                    "email": "test@example.com",
                },
            },
        )
    )
    client = OcmoClient(config=_config())
    who = client.whoami()
    assert who.display_name == "Test User"
    assert who.user_details.email == "test@example.com"
    client.close()


def test_namespace_view_exposes_list_locks(respx_mock):
    respx_mock.get(f"{_SERVER}/api/v1/ns/prod/~lock/").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 1,
                "locks": [
                    {
                        "path": "app/web",
                        "reason": "deploy",
                        "locked_by": "ci",
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ],
            },
        )
    )
    client = OcmoClient(config=_config())
    locks = client.ns("prod").list_locks()
    assert locks.count == 1
    assert locks.locks[0].path == "app/web"
    client.close()


def test_facade_maps_error_schema_to_sdk_error(respx_mock):
    respx_mock.get(f"{_SERVER}/api/v1/ns/prod/~get/missing").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )
    client = OcmoClient(config=_config())
    with pytest.raises(OcmoNotFoundError, match="not found"):
        client.ns("prod").get_item("missing")
    client.close()


def test_no_client_api_attribute():
    client = OcmoClient(config=_config())
    assert not hasattr(client, "api")
    client.close()


def test_prepare_kwargs_explicit_body_drops_flat_fields():
    from ocmo._facade_runtime import prepare_kwargs
    from ocmo._generated.types import UNSET

    prepared = prepare_kwargs(
        "create_namespace",
        {"name": UNSET, "description": UNSET, "body": {"name": "my-ns"}},
    )
    assert list(prepared.keys()) == ["body"]
    assert prepared["body"].name == "my-ns"


def test_prepare_kwargs_explicit_body_drops_duplicate_flat_values():
    from ocmo._facade_runtime import prepare_kwargs

    prepared = prepare_kwargs(
        "create_global_permission",
        {
            "namespace": "dev/*",
            "id": "rule-1",
            "body": {"namespace": "dev/*", "id": "rule-1", "read": {"allow": True}},
        },
    )
    assert list(prepared.keys()) == ["body"]
