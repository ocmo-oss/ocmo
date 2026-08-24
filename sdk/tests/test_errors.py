"""Tests for the exception hierarchy and error normalisation."""

import pytest

from ocmo.errors import (
    OcmoAPIError,
    OcmoAuthError,
    OcmoConflictError,
    OcmoLockedError,
    OcmoNotFoundError,
    OcmoPermissionError,
    OcmoValidationError,
    error_body_from_response,
    raise_for_response,
)


def _raise(status: int, body: dict) -> None:
    raise_for_response(status_code=status, method="GET", path="/test", body=body)


def test_404_raises_not_found():
    with pytest.raises(OcmoNotFoundError) as exc_info:
        _raise(404, {"error": "config not found"})
    assert "config not found" in str(exc_info.value)
    assert exc_info.value.status_code == 404


def test_409_raises_conflict():
    with pytest.raises(OcmoConflictError):
        _raise(409, {"error": "conflict"})


def test_401_raises_auth_error():
    with pytest.raises(OcmoAuthError):
        _raise(401, {"detail": "Invalid token"})


def test_403_raises_permission_error():
    with pytest.raises(OcmoPermissionError):
        _raise(403, {"error": "forbidden"})


def test_423_raises_locked_error():
    with pytest.raises(OcmoLockedError) as exc_info:
        _raise(423, {"error": "path is locked", "lock_path": "/app", "reason": "deploy"})
    err = exc_info.value
    assert err.lock_path == "/app"
    assert err.reason == "deploy"


def test_422_raises_validation_error():
    with pytest.raises(OcmoValidationError) as exc_info:
        _raise(422, {"error": ["field required", "invalid value"]})
    err = exc_info.value
    assert isinstance(err.errors, list)
    assert len(err.errors) == 2


def test_422_uses_explicit_errors_list():
    with pytest.raises(OcmoValidationError) as exc_info:
        _raise(
            422,
            {
                "error": "name: Field required",
                "errors": ["name: Field required", "description: Field required"],
            },
        )
    err = exc_info.value
    assert err.errors == ["name: Field required", "description: Field required"]
    assert err.message == "name: Field required"


def test_normalises_detail_key():
    with pytest.raises(OcmoNotFoundError) as exc_info:
        _raise(404, {"detail": "Not found"})
    assert "Not found" in str(exc_info.value)


def test_api_error_carries_metadata():
    with pytest.raises(OcmoNotFoundError) as exc_info:
        _raise(404, {"error": "x", "audit_event_id": "evt-123"})
    assert exc_info.value.audit_event_id == "evt-123"
    assert exc_info.value.method == "GET"
    assert exc_info.value.path == "/test"


def test_api_error_repr_has_no_headers():
    """OcmoAPIError repr must not expose request headers (§13.1)."""
    err = OcmoAPIError("msg", status_code=500, method="POST", path="/x")
    assert "Authorization" not in repr(err)
    assert "header" not in repr(err).lower()


def test_error_body_from_response_strips_html_404():
    html = (
        "<!DOCTYPE html><html><head>"
        "<title>Page not found at /api/v1/ns/prod/~resolve/</title>"
        "</head><body>...</body></html>"
    )
    body = error_body_from_response(
        status_code=404,
        content=html.encode(),
        content_type="text/html; charset=utf-8",
    )
    assert body == {"error": "Not found: /api/v1/ns/prod/~resolve/"}
