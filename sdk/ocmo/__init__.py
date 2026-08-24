"""OCMO Python SDK — public facade.

Quick start::

    from ocmo import OcmoClient

    client = OcmoClient()                    # reads OCMO_* env vars
    client.whoami()
    client.ns("prod").list_locks()
    result = client.ns("prod").resolve("app/web", cast="json")
    data   = result["app.json"].data         # parsed dict, lazy
    host   = result["app.json"].get("database.host")

Every REST operation is a method on :class:`OcmoClient` or :class:`~ocmo.client.NamespaceView`.
The generated layer (``ocmo._generated``) is internal and must not be imported directly.
Request/response models are available from :mod:`ocmo.models`.
"""

from ._version import __version__
from .client import AsyncNamespaceView, AsyncOcmoClient, NamespaceView, OcmoClient
from .config import OcmoConfig
from .errors import (
    ArtifactExpiredError,
    ChecksumMismatchError,
    NoArtifactError,
    OcmoAPIError,
    OcmoArtifactError,
    OcmoAuthError,
    OcmoConfigError,
    OcmoConflictError,
    OcmoError,
    OcmoIncompatibleVersionError,
    OcmoLockedError,
    OcmoNotFoundError,
    OcmoPayloadTooLargeError,
    OcmoPermissionError,
    OcmoTransportError,
    OcmoValidationError,
    PropertyNotFoundError,
    UnstructuredFormatError,
)
from .models import CanIRequestSchema, LockPayload, LockSchema
from .resolve import (
    AsyncResolvedItem,
    AsyncResolveResult,
    ResolvedItem,
    ResolverConfig,
    ResolveResult,
    ResolverHooks,
)

__all__ = [
    "__version__",
    # Clients
    "OcmoClient",
    "AsyncOcmoClient",
    "NamespaceView",
    "AsyncNamespaceView",
    # Configuration
    "OcmoConfig",
    # API models
    "CanIRequestSchema",
    "LockPayload",
    "LockSchema",
    # Resolve model
    "ResolveResult",
    "ResolvedItem",
    "AsyncResolveResult",
    "AsyncResolvedItem",
    "ResolverConfig",
    "ResolverHooks",
    # Errors
    "OcmoError",
    "OcmoConfigError",
    "OcmoAuthError",
    "OcmoPermissionError",
    "OcmoAPIError",
    "OcmoNotFoundError",
    "OcmoConflictError",
    "OcmoLockedError",
    "OcmoValidationError",
    "OcmoPayloadTooLargeError",
    "OcmoTransportError",
    "OcmoArtifactError",
    "ArtifactExpiredError",
    "ChecksumMismatchError",
    "NoArtifactError",
    "UnstructuredFormatError",
    "PropertyNotFoundError",
    "OcmoIncompatibleVersionError",
]
