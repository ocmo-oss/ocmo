"""Human-readable formatting for Pydantic validation errors."""

from __future__ import annotations

from typing import Any, cast

from pydantic import ValidationError as PydanticValidationError

_PARAM_SOURCES = frozenset({"body", "query", "path", "header", "form", "cookie"})


def _format_field_path(parts: list[str]) -> str:
    """Render nested field locations, including numeric list indices."""
    result = ""
    for part in parts:
        if part.isdigit():
            result += f"[{part}]"
        elif result:
            result += f".{part}"
        else:
            result = part
    return result


def _format_location(loc: tuple[Any, ...] | list[Any]) -> str:
    """Turn a Pydantic/Ninja ``loc`` tuple into a stable field identifier."""
    parts = [str(part) for part in loc]
    if not parts:
        return ""

    if parts[0] in _PARAM_SOURCES:
        source, *path = parts
        if not path:
            return ""
        field = _format_field_path(path)
        return field if source == "body" else f"{source}.{field}"

    if parts[0] == "response":
        _, *path = parts
        if not path:
            return "response"
        return _format_field_path(path)

    return _format_field_path(parts)


def _extract_validation_message(err: dict[str, Any]) -> str:
    """Return the most helpful message for a single validation error item."""
    ctx = err.get("ctx") or {}
    if "error" in ctx:
        return str(ctx["error"])

    message = str(err.get("msg", "Invalid value"))
    if message.startswith("Value error, "):
        return message.removeprefix("Value error, ")
    return message


def format_validation_error_item(err: dict[str, Any]) -> str:
    """Format one Pydantic/Ninja validation error entry."""
    location = _format_location(err.get("loc", ()))
    message = _extract_validation_message(err)
    if location:
        return f"{location}: {message}"
    return message


def format_ninja_validation_errors(errors: list[dict[str, Any]]) -> list[str]:
    """Format django-ninja request validation errors."""
    return [format_validation_error_item(err) for err in errors]


def format_pydantic_validation_error(exc: PydanticValidationError) -> list[str]:
    """Format a raw Pydantic validation error."""
    return format_ninja_validation_errors(cast("list[dict[str, Any]]", exc.errors(include_url=False)))


def format_pydantic_validation_error_with_prefix(
    exc: PydanticValidationError,
    *,
    prefix: str = "",
) -> list[str]:
    """Format Pydantic errors with an optional dotted field prefix."""
    messages = format_pydantic_validation_error(exc)
    if not prefix:
        return messages

    normalized_prefix = prefix if prefix.endswith(".") else f"{prefix}."
    prefixed: list[str] = []
    for message in messages:
        if ": " in message:
            field, separator, rest = message.partition(": ")
            prefixed.append(f"{normalized_prefix}{field}{separator}{rest}")
        else:
            prefixed.append(f"{normalized_prefix}{message}")
    return prefixed


def is_response_validation_error(exc: PydanticValidationError) -> bool:
    """Return whether *exc* refers to response schema validation."""
    for err in exc.errors(include_url=False):
        loc = err.get("loc", ())
        if loc and loc[0] == "response":
            return True
    return False
