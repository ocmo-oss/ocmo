"""In-process LRU cache for resolved webhook configs."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass

from django.conf import settings

from ...schemas.webhooks import WebhooksConfig
from ..tree_capabilities import normalize_tree_path


@dataclass(frozen=True)
class _CachedWebhooksEntry:
    """Resolved webhook config plus secret paths consulted during resolve."""

    config: WebhooksConfig
    secret_paths: frozenset[str]


class _LRUCache:
    def __init__(self, size_setting: str, default_size: int) -> None:
        self._size_setting = size_setting
        self._default_size = default_size
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    @property
    def _max_size(self) -> int:
        return getattr(settings, self._size_setting, self._default_size)

    def get(self, namespace_id: int):
        with self._lock:
            if namespace_id in self._data:
                self._data.move_to_end(namespace_id)
                return self._data[namespace_id]
        return None

    def put(self, namespace_id: int, value) -> None:
        with self._lock:
            if namespace_id in self._data:
                self._data.move_to_end(namespace_id)
                self._data[namespace_id] = value
                return
            self._data[namespace_id] = value
            max_size = self._max_size
            while len(self._data) > max_size:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def invalidate_namespace(self, namespace_id: int) -> None:
        with self._lock:
            self._data.pop(namespace_id, None)

    def invalidate_namespace_secret(self, namespace_id: int, secret_path: str) -> None:
        normalized = normalize_tree_path(secret_path)
        with self._lock:
            entry = self._data.get(namespace_id)
            if entry is not None and normalized in entry.secret_paths:
                del self._data[namespace_id]


config_cache = _LRUCache("OCMO_WEBHOOKS_CACHE_SIZE", 256)
