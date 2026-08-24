"""Resolver service-account accessor.

Loads a Resolver tree item via TreeManager, validates that it belongs to the
requested namespace, and exposes the resolver's scope and resolving configuration.
"""

from __future__ import annotations

from ..exceptions import ResolverNamespaceMismatch
from ..schemas.generic import ResolverConfigurationSchema
from ..shortcuts import safe_yaml_load
from .auth import AuthManager
from .tree import TreeManager


class ResolverManager:
    """Thin accessor for a Resolver's scope and resolving configuration."""

    def __init__(self, namespace, auth: AuthManager):
        if not auth.is_resolver:
            raise ResolverNamespaceMismatch("ResolverManager requires resolver authentication")
        if auth.namespace_id != namespace.id:
            raise ResolverNamespaceMismatch("Resolver token does not belong to the requested namespace")
        self.namespace = namespace
        resolver_path = auth.resolver_path or ""
        self.resolver = TreeManager(namespace, resolver_path, auth=None).get_or_raise(["resolver"])
        # Derive scope from the loaded item's path (authoritative).
        self.scope: str = "/".join(self.resolver.path.split("/")[:-1])

    @property
    def configuration(self) -> ResolverConfigurationSchema:
        raw = self.resolver.configuration or {}
        if isinstance(raw, str):
            raw = safe_yaml_load(raw) or {}
        return ResolverConfigurationSchema.model_validate(raw)

    def scoped_path(self, requested_path: str) -> str:
        """Map a caller-supplied path to the resolver's scope.

        ``requested_path == '.'`` resolves to the scope root itself.
        Any other value is joined onto the scope as a relative path.
        """
        requested = requested_path.strip("/")
        if requested == ".":
            return self.scope
        combined = f"{self.scope}/{requested}" if self.scope else requested
        parts: list[str] = []
        for segment in combined.split("/"):
            if not segment or segment == ".":
                continue
            if segment == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(segment)
        return "/".join(parts)
