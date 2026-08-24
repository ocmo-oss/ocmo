"""Exception hierarchy for the OCMO SDK."""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import Any


class OcmoError(Exception):
    """Base class for all OCMO SDK exceptions."""


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class OcmoConfigError(OcmoError):
    """Bad or missing configuration, raised before any network request."""


# ---------------------------------------------------------------------------
# Auth errors
# ---------------------------------------------------------------------------


class OcmoAuthError(OcmoError):
    """401 responses or token-acquisition failures."""


class OcmoPermissionError(OcmoAuthError):
    """403 — authenticated but not authorised."""


# ---------------------------------------------------------------------------
# API errors (non-2xx with a server payload)
# ---------------------------------------------------------------------------


class OcmoAPIError(OcmoError):
    """Any non-2xx response carrying a server error payload."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        method: str,
        path: str,
        audit_event_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.method = method
        self.path = path
        self.audit_event_id = audit_event_id

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status_code={self.status_code}, "
            f"method={self.method!r}, path={self.path!r}, message={self.message!r})"
        )


class OcmoNotFoundError(OcmoAPIError):
    """404 — resource not found."""


class OcmoConflictError(OcmoAPIError):
    """409 — resource conflict."""


class OcmoLockedError(OcmoAPIError):
    """423 — path is locked; exposes `.lock_path` and `.reason`."""

    def __init__(self, message: str, *, lock_path: str, reason: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.lock_path = lock_path
        self.reason = reason


class OcmoValidationError(OcmoAPIError):
    """422 — request validation failure; `.errors` is the list of detail items."""

    def __init__(self, message: str, *, errors: list[Any], **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.errors = errors


class OcmoPayloadTooLargeError(OcmoAPIError):
    """413 — request body exceeds server limit."""


# ---------------------------------------------------------------------------
# Transport errors
# ---------------------------------------------------------------------------


class OcmoTransportError(OcmoError):
    """Connection, TLS, or timeout failure."""


# ---------------------------------------------------------------------------
# Artifact / resolve errors
# ---------------------------------------------------------------------------


class OcmoArtifactError(OcmoError):
    """Base for artifact-level failures."""


class ArtifactExpiredError(OcmoArtifactError):
    """Download URL has expired; a re-resolve + retry did not succeed."""


class ChecksumMismatchError(OcmoArtifactError):
    """Downloaded bytes do not match the expected checksum."""

    def __init__(self, name: str, expected: str, actual: str) -> None:
        super().__init__(f"Checksum mismatch for {name!r}: expected {expected}, got {actual}")
        self.name = name
        self.expected = expected
        self.actual = actual


class NoArtifactError(OcmoArtifactError):
    """Artifact bytes requested but the resolve was made with `trace_only=True`."""

    def __init__(self, name: str) -> None:
        super().__init__(f"No artifact available for {name!r}: the resolve was made with trace_only=True.")
        self.name = name


class UnstructuredFormatError(OcmoArtifactError):
    """Structured access requested on a non-JSON/YAML artifact."""

    def __init__(self, name: str, fmt: str) -> None:
        super().__init__(
            f"Cannot perform structured access on {name!r}: format is {fmt!r} "
            "(structured access is only supported for json and yaml)."
        )
        self.name = name
        self.format = fmt


class PropertyNotFoundError(OcmoArtifactError):
    """Dotted-path lookup failed and no default was supplied."""

    def __init__(self, path: str, item_name: str) -> None:
        super().__init__(f"Property {path!r} not found in {item_name!r}")
        self.path = path
        self.item_name = item_name


# ---------------------------------------------------------------------------
# Version compatibility errors
# ---------------------------------------------------------------------------


class OcmoIncompatibleVersionError(OcmoError):
    """SDK and API are on different major versions — not compatible."""

    def __init__(self, sdk_version: str, api_version: str) -> None:
        super().__init__(
            f"SDK version {sdk_version} is not compatible with API version {api_version}: "
            "major versions differ. Upgrade both components to the same major version."
        )
        self.sdk_version = sdk_version
        self.api_version = api_version


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_HTML_MARKERS = ("<!DOCTYPE", "<html")


def _looks_like_html(text: str) -> bool:
    head = text.lstrip()[:256].upper()
    return any(marker in head for marker in _HTML_MARKERS)


def _extract_html_title(text: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def error_body_from_response(
    *,
    status_code: int,
    content: bytes,
    content_type: str = "",
) -> dict[str, Any]:
    """Build a JSON-like error body from an HTTP error response."""
    text = content.decode("utf-8", errors="replace").strip()
    if "json" in content_type.lower() and text:
        try:
            import json

            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    if text and _looks_like_html(text):
        title = _extract_html_title(text)
        if title:
            not_found_prefix = "Page not found at "
            if status_code == 404 and title.startswith(not_found_prefix):
                return {"error": f"Not found: {title[len(not_found_prefix):]}"}
            return {"error": title}
        try:
            phrase = HTTPStatus(status_code).phrase
        except ValueError:
            phrase = f"HTTP {status_code}"
        return {"error": phrase}

    if not text:
        try:
            phrase = HTTPStatus(status_code).phrase
        except ValueError:
            phrase = f"HTTP {status_code}"
        return {"error": phrase}

    if len(text) > 500:
        text = text[:500] + "..."
    return {"error": text}


_STATUS_MAP: dict[int, type[OcmoAPIError]] = {
    404: OcmoNotFoundError,
    409: OcmoConflictError,
    413: OcmoPayloadTooLargeError,
}


def raise_for_response(
    *,
    status_code: int,
    method: str,
    path: str,
    body: dict[str, Any],
) -> None:
    """Parse a server error body and raise the appropriate SDK exception.

    Normalises both ``{"error": "…"}`` and ``{"detail": "…"}`` shapes.
    """
    # Normalise message
    raw = body.get("error") or body.get("detail") or body.get("message") or str(body)
    if isinstance(raw, list):
        message = "; ".join(str(e) for e in raw)
    else:
        message = str(raw)

    audit_event_id: str | None = body.get("audit_event_id")
    base_kwargs: dict[str, Any] = {
        "status_code": status_code,
        "method": method,
        "path": path,
        "audit_event_id": audit_event_id,
    }

    if status_code == 401:
        raise OcmoAuthError(message)
    if status_code == 403:
        raise OcmoPermissionError(message)
    if status_code == 423:
        raise OcmoLockedError(
            message,
            lock_path=body.get("lock_path", ""),
            reason=body.get("reason", ""),
            **base_kwargs,
        )
    if status_code == 422:
        errors_raw = body.get("errors")
        if errors_raw is None:
            if isinstance(raw, list):
                errors_raw = raw
            else:
                errors_raw = [raw]
        raise OcmoValidationError(message, errors=errors_raw, **base_kwargs)

    cls: type[OcmoAPIError] = _STATUS_MAP.get(status_code, OcmoAPIError)
    raise cls(message, **base_kwargs)
