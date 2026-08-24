class NamespaceConflict(Exception):
    pass


class FolderCannotBeExplicitlyCreated(Exception):
    pass


class ConflictPathsDetected(Exception):
    pass


class WrongMoveTargetException(Exception):
    pass


class WrongCopyTargetException(Exception):
    pass


class TreeItemConflict(Exception):
    pass


class VersionNotFound(Exception):
    pass


class ConfigTagAlreadyPointsToDesiredVersion(Exception):
    pass


class ConfigTagDoesntExists(Exception):
    pass


class ReservedTagsCantBeSet(Exception):
    pass


class ActiveTagCannotBeDeleted(Exception):
    pass


class NamespaceActiveTagNotFound(Exception):
    pass


class InvalidResolverToken(Exception):
    pass


class ResolverNamespaceMismatch(Exception):
    """Resolver token is valid but belongs to a different namespace."""

    pass


class UnknownCastFormat(Exception):
    pass


class CannotCast(Exception):
    pass


class CannotResolveConfig(Exception):
    pass


class ConfigExtendNotPossible(Exception):
    pass


class UnknownCastOption(Exception):
    pass


class InvalidCastOption(Exception):
    pass


class ParameterError(Exception):
    """Invalid declared parameter, missing reference, or substitution failure."""

    pass


class SecretParameterError(Exception):
    """Failure to resolve a secret parameter (missing secret, field, multi-line value)."""

    pass


class TemplateRenderError(Exception):
    """Runtime Jinja2 rendering failure."""

    pass


class InvalidResolveToken(Exception):
    """Signed artifact download token is missing/invalid/expired."""

    pass


class UploadTooLarge(Exception):
    """Uploaded document exceeds the configured byte limit for its item type."""

    pass


class LockAlreadyExists(Exception):
    """An active lock already exists at this path."""

    pass


class Unauthenticated(Exception):
    """Request carries no valid authentication credential."""

    pass


class PermissionDenied(Exception):
    """Caller lacks the required permission for the requested operation."""

    pass


class CapabilityDenied(Exception):
    """Internal signal that a tree-item capability check failed.

    Not raised to HTTP clients directly. Caught by require_permissions
    (or explicit helpers) and converted to PermissionDenied (403).
    """

    pass


class NotFound(Exception):
    """Resource not found (used to mask auth errors as 404)."""

    pass


class BrokenNamespace(Exception):
    """Namespace is in an inconsistent state (e.g. missing _permissions config or version)."""

    pass


class PathLocked(Exception):
    """A tree mutation was blocked by an active lock on an ancestor path."""

    def __init__(self, lock_path: str, reason: str):
        self.lock_path = lock_path
        self.reason = reason
        super().__init__(f"Path is locked by freeze at '{lock_path}': {reason}")


class PropagationNotConfigured(Exception):
    """Propagation is not configured, disabled, or trigger does not match."""

    pass
