"""Map SDK exceptions to CLI exit codes and human-readable messages."""

from __future__ import annotations

import functools
import sys
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from . import _exit

P = ParamSpec("P")
R = TypeVar("R")


def handle_sdk_error(exc: Exception) -> None:
    """Print an error message and raise SystemExit with the right exit code.

    Import the error hierarchy lazily so this module itself is cheap to import.
    """
    # Lazy import to keep startup time low
    from ocmo.errors import (  # noqa: I001
        OcmoAPIError,
        OcmoAuthError,
        OcmoConfigError,
        OcmoConflictError,
        OcmoIncompatibleVersionError,
        OcmoLockedError,
        OcmoNotFoundError,
        OcmoPayloadTooLargeError,
        OcmoPermissionError,
        OcmoTransportError,
        OcmoValidationError,
    )

    if isinstance(exc, OcmoConfigError):
        _die(str(exc), _exit.FAILURE)
    elif isinstance(exc, OcmoIncompatibleVersionError):
        _die(str(exc), _exit.FAILURE)
    elif isinstance(exc, OcmoPermissionError):
        _die(str(exc), _exit.AUTH_ERROR)
    elif isinstance(exc, OcmoAuthError):
        _die(str(exc), _exit.AUTH_ERROR)
    elif isinstance(exc, OcmoNotFoundError):
        _die(str(exc), _exit.NOT_FOUND)
    elif isinstance(exc, OcmoConflictError):
        _die(str(exc), _exit.CONFLICT)
    elif isinstance(exc, OcmoLockedError):
        _die(
            f"{exc} (lock path: {exc.lock_path}, reason: {exc.reason})",
            _exit.LOCKED,
        )
    elif isinstance(exc, OcmoValidationError | OcmoPayloadTooLargeError):
        detail = _format_validation_errors(getattr(exc, "errors", None))
        _die(detail if detail else str(exc), _exit.VALIDATION_ERROR)
    elif isinstance(exc, OcmoTransportError):
        _die(str(exc), _exit.FAILURE)
    elif isinstance(exc, OcmoAPIError):
        msg = str(exc)
        if exc.method and exc.path and exc.method != "HTTP":
            msg = f"{exc.method} {exc.path}: {msg}"
        elif exc.path:
            msg = f"{exc.path}: {msg}"
        code = exc.status_code if 400 <= exc.status_code < 600 else _exit.FAILURE
        if exc.status_code == 404:
            code = _exit.NOT_FOUND
        elif exc.status_code == 409:
            code = _exit.CONFLICT
        elif exc.status_code == 422:
            code = _exit.VALIDATION_ERROR
        _die(msg, code)
    else:
        _die(str(exc), _exit.FAILURE)


def _die(msg: str, code: int) -> None:
    msg = msg.rstrip("\n")
    if "\n" in msg or msg.startswith("  -"):
        print(f"Error:\n{msg}", file=sys.stderr)
    else:
        print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _format_validation_errors(errors: Any) -> str:
    if not errors:
        return ""
    if isinstance(errors, list):
        lines: list[str] = []
        for item in errors:
            if isinstance(item, dict):
                loc = item.get("loc") or item.get("field")
                msg = item.get("msg") or item.get("message") or item.get("error")
                if loc and msg:
                    if isinstance(loc, list | tuple):
                        loc = _format_validation_location(loc)
                    lines.append(f"  - {loc}: {msg}")
                elif msg:
                    lines.append(f"  - {msg}")
                else:
                    lines.append(f"  - {item}")
            elif isinstance(item, str) and ": " in item:
                field, _, message = item.partition(": ")
                lines.append(f"  - {field}: {message}")
            else:
                lines.append(f"  - {item}")
        return "\n".join(lines)
    return f"  - {errors}"


def _format_validation_location(loc: tuple[Any, ...] | list[Any]) -> str:
    parts = [str(part) for part in loc]
    if not parts:
        return ""
    if parts[0] in {"body", "query", "path", "header", "form", "cookie"}:
        source, *path = parts
        if not path:
            return source
        field = _format_validation_field_path(path)
        return field if source == "body" else f"{source}.{field}"
    return _format_validation_field_path(parts)


def _format_validation_field_path(parts: list[str]) -> str:
    result = ""
    for part in parts:
        if part.isdigit():
            result += f"[{part}]"
        elif result:
            result += f".{part}"
        else:
            result = part
    return result


def sdk_command(fn: Callable[P, R]) -> Callable[P, R]:
    """Decorator that wraps a click command body to catch SDK errors."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except KeyboardInterrupt:
            raise SystemExit(_exit.INTERRUPTED)
        except SystemExit:
            raise
        except Exception as exc:
            handle_sdk_error(exc)
            raise AssertionError("handle_sdk_error always exits") from exc

    return wrapper
