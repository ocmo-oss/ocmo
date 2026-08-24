"""Shared helpers for API error responses."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError

from ..validation_errors import (
    format_ninja_validation_errors,
    format_pydantic_validation_error,
    is_response_validation_error,
)

__all__ = [
    "create_error_response",
    "error_payload",
    "format_django_validation_error",
    "format_ninja_validation_errors",
    "format_pydantic_validation_error",
    "is_response_validation_error",
]


def format_django_validation_error(exc: DjangoValidationError) -> list[str]:
    """Return human-readable validation messages with field names when available."""
    message_dict = getattr(exc, "message_dict", None)
    if message_dict:
        lines: list[str] = []
        for field, messages in message_dict.items():
            for message in messages:
                if field in (None, "__all__"):
                    lines.append(str(message))
                else:
                    lines.append(f"{field}: {message}")
        return lines
    return [str(message) for message in exc.messages]


def audit_event_id_from_exception(exc: BaseException) -> str | None:
    """Return audit event UUID attached to *exc*, if any."""
    audit_id = getattr(exc, "audit_event_id", None)
    if audit_id is None:
        return None
    return str(audit_id)


def error_payload(exc: BaseException, error: Any, **extra: Any) -> dict[str, Any]:
    """Build a JSON error body, including audit_event_id when present on *exc*."""
    payload: dict[str, Any] = {"error": error, **extra}
    if isinstance(error, list):
        payload["errors"] = error
    audit_id = audit_event_id_from_exception(exc)
    if audit_id:
        payload["audit_event_id"] = audit_id
    return payload


def create_error_response(api, request, exc: BaseException, error: Any, status: int, **extra: Any):
    """Create a Ninja response for an application error."""
    return api.create_response(
        request,
        error_payload(exc, error, **extra),
        status=status,
    )
