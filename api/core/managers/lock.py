from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.utils import timezone

from ..decorators import PermCheck, audit, require_permissions, webhook
from ..exceptions import LockAlreadyExists, PathLocked
from ..models import TreeItem, TreeLock
from ..shortcuts import validate_path_characters
from .auth import AuthManager

logger = logging.getLogger(__name__)


def _lock_details(schema: dict) -> dict:
    """Serialize datetime fields in a lock schema dict for webhook payloads."""
    if not schema:
        return {}
    return {
        "reason": schema.get("reason"),
        "expires_at": schema["expires_at"].isoformat() if schema.get("expires_at") else None,
        "locked_by": schema.get("locked_by"),
        "created_at": schema["created_at"].isoformat() if schema.get("created_at") else None,
        "updated_at": schema["updated_at"].isoformat() if schema.get("updated_at") else None,
    }


class LockManager:
    """CRUD and coverage queries for namespace tree locks."""

    def __init__(self, namespace, path: str, *, auth):
        self.namespace = namespace
        self.path = self._normalize_lock_path(path)
        if self.path != "*":
            validate_path_characters(self.path)
        self.auth = auth

    @staticmethod
    def _normalize_lock_path(path: str) -> str:
        """Normalize a lock/tree path (no leading or trailing slashes)."""
        if path.startswith("/"):
            raise ValidationError("Path can't start with '/'")
        normalized = path.removesuffix("/")
        if any(part.strip() == "" for part in normalized.split("/") if normalized) and normalized != "":
            raise ValidationError("Path can't have a segment that is empty or whitespace only")
        return normalized

    @staticmethod
    def _path_prefixes(path: str) -> list[str]:
        """Ancestor paths including the path itself (for covering-lock lookup)."""
        if path == "":
            return [""]
        parts = [part for part in path.split("/") if part]
        return ["/".join(parts[: i + 1]) for i in range(len(parts))]

    @staticmethod
    def _active_filter() -> Q:
        now = timezone.now()
        return Q(expires_at__isnull=True) | Q(expires_at__gt=now)

    @staticmethod
    def _locks_queryset(namespace):
        return TreeLock.objects.filter(namespace=namespace).filter(LockManager._active_filter())

    def _require_tree_item(self, path: str) -> None:
        if not TreeItem.objects.filter(namespace=self.namespace, path=path).exists():
            raise TreeItem.DoesNotExist(f"No tree item exists at path '{path}'; locks require an existing path")

    @staticmethod
    def _to_schema(lock: TreeLock) -> dict:
        return {
            "path": lock.path,
            "reason": lock.reason,
            "expires_at": lock.expires_at,
            "locked_by": lock.locked_by,
            "created_at": lock.created_at,
            "updated_at": lock.updated_at,
        }

    @audit("lock", object_id_attr=lambda self: "*", operation="List locks")
    @require_permissions(PermCheck("lock:read", resource=lambda self: ""))
    def list_active(self, *, limit=100, offset=0) -> dict:
        qs = self._locks_queryset(self.namespace).order_by("path")
        count = qs.count()
        locks = qs[offset : offset + limit]
        items = [self._to_schema(lock) for lock in locks]
        return {"locks": items, "count": count}

    @audit("lock", operation="Read lock")
    @require_permissions(PermCheck("lock:read"))
    def get(self) -> dict:
        if self.path == "*":
            raise ValidationError("Not valid lock path")
        try:
            lock = TreeLock.objects.get(namespace=self.namespace, path=self.path)
        except TreeLock.DoesNotExist:
            raise TreeLock.DoesNotExist(f"Lock not found at path '{self.path}'")
        if not lock.is_active:
            raise TreeLock.DoesNotExist(f"Lock not found at path '{self.path}'")
        return self._to_schema(lock)

    def _actor_identity(self) -> str:
        return AuthManager.resolve_actor_identity(self.auth)

    @webhook(
        lambda self, result, bound: getattr(self, "_lock_event", "lock.created"),
        details=lambda self, result, bound: _lock_details(result),
    )
    @audit("lock", operation="Create lock")
    @require_permissions(PermCheck("lock:write"))
    def create(
        self,
        *,
        reason: str,
        expires_at: datetime | None = None,
    ) -> dict:
        self._require_tree_item(self.path)
        locked_by = self._actor_identity()

        with transaction.atomic():
            existing = TreeLock.objects.filter(namespace=self.namespace, path=self.path).first()
            if existing is not None:
                if existing.is_active:
                    raise LockAlreadyExists(f"Path '{self.path}' is already locked")
                existing.reason = reason
                existing.expires_at = expires_at
                existing.locked_by = locked_by
                existing.save()
                self._lock_event = "lock.updated"
                return self._to_schema(existing)

            try:
                lock = TreeLock.objects.create(
                    namespace=self.namespace,
                    path=self.path,
                    reason=reason,
                    expires_at=expires_at,
                    locked_by=locked_by,
                )
            except IntegrityError:
                raise LockAlreadyExists(f"Path '{self.path}' is already locked") from None
        self._lock_event = "lock.created"
        return self._to_schema(lock)

    @webhook("lock.updated", details=lambda self, result, bound: _lock_details(result))
    @audit("lock", operation="Update lock")
    @require_permissions(PermCheck("lock:write"))
    def replace(
        self,
        *,
        reason: str,
        expires_at: datetime | None = None,
    ) -> dict:
        if self.path == "*":
            raise ValidationError("Not valid lock path")
        try:
            lock = TreeLock.objects.get(namespace=self.namespace, path=self.path)
        except TreeLock.DoesNotExist:
            raise TreeLock.DoesNotExist(f"Lock not found at path '{self.path}'")
        lock.reason = reason
        lock.expires_at = expires_at
        locked_by = self._actor_identity()
        if locked_by:
            lock.locked_by = locked_by
        lock.save()
        return self._to_schema(lock)

    @webhook(
        "lock.deleted",
        details=lambda self, result, bound: _lock_details(getattr(self, "_lock_schema", {})),
    )
    @audit("lock", operation="Delete lock")
    @require_permissions(PermCheck("lock:delete"))
    def delete(self) -> None:
        if self.path == "*":
            raise ValidationError("Not valid lock path")
        lock = TreeLock.objects.filter(namespace=self.namespace, path=self.path).first()
        if lock is None:
            raise TreeLock.DoesNotExist(f"Lock not found at path '{self.path}'")
        self._lock_schema = self._to_schema(lock)
        lock.delete()

    @staticmethod
    def get_covering_lock(namespace, for_path: str) -> TreeLock | None:
        normalized = LockManager._normalize_lock_path(for_path)
        prefixes = LockManager._path_prefixes(normalized)
        return LockManager._locks_queryset(namespace).filter(path__in=prefixes).order_by("-path").first()

    @staticmethod
    def ensure_path_writable(namespace, for_path: str) -> None:
        lock = LockManager.get_covering_lock(namespace, for_path)
        if lock is not None:
            raise PathLocked(lock.path, lock.reason)

    @staticmethod
    def get_lock_in_subtree(namespace, prefix_path: str) -> TreeLock | None:
        """Return an active lock on *prefix_path* or any path under it."""
        normalized = LockManager._normalize_lock_path(prefix_path)
        if not normalized:
            return None
        return (
            LockManager._locks_queryset(namespace)
            .filter(Q(path=normalized) | Q(path__startswith=f"{normalized}/"))
            .order_by("path")
            .first()
        )

    @staticmethod
    def ensure_subtree_writable(namespace, prefix_path: str) -> None:
        lock = LockManager.get_lock_in_subtree(namespace, prefix_path)
        if lock is not None:
            raise PathLocked(lock.path, lock.reason)

    @staticmethod
    def ensure_paths_writable(namespace, paths: Iterable[str]) -> None:
        seen: set[str] = set()
        for raw in paths:
            normalized = LockManager._normalize_lock_path(raw)
            if normalized in seen:
                continue
            seen.add(normalized)
            LockManager.ensure_path_writable(namespace, normalized)
