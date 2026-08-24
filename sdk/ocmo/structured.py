"""Lazy structured property access for JSON/YAML resolved items.

Supported path grammar (deliberately small — full JSONPath is a non-goal):

    a.b.c          — nested dict keys
    a[0].b         — list index inside a dict
    a.b[1][2]      — chained list indexes

Keys containing '.' or '[' are NOT addressable via path strings; use the
mapping API instead: ``item.data["odd.key"]``.
"""

from __future__ import annotations

import re
from typing import Any

from .errors import PropertyNotFoundError, UnstructuredFormatError

_STRUCTURED_FORMATS = frozenset({"json", "yaml"})

# Tokenise a dotted/index path: "a.b[0].c" → ["a", "b", 0, "c"]
_SEGMENT_RE = re.compile(r"\[(\d+)\]|([^.\[]+)")


def _parse_path(path: str) -> list[str | int]:
    segments: list[str | int] = []
    for m in _SEGMENT_RE.finditer(path):
        if m.group(1) is not None:
            segments.append(int(m.group(1)))
        else:
            segments.append(m.group(2))
    return segments


_SENTINEL = object()


def path_get(data: Any, path: str, default: Any = _SENTINEL) -> Any:
    """Traverse *data* along *path*; raise :exc:`PropertyNotFoundError` when missing.

    ``default`` MUST be supplied explicitly to accept ``None`` as a valid value.
    Omitting it intentionally raises rather than returning ``None``.
    """
    segments = _parse_path(path)
    node: Any = data
    for seg in segments:
        try:
            node = node[seg]
        except (KeyError, IndexError, TypeError):
            if default is _SENTINEL:
                raise PropertyNotFoundError(path, item_name="<data>")
            return default
    return node


class StructuredMixin:
    """Mixin that adds structured property access to a ``ResolvedItem``.

    Subclasses must provide:
      - ``name: str``
      - ``format: str``
      - ``_get_bytes() -> bytes``  (the lazy artifact fetch)
      - ``_parsed_data: Any | None`` cache slot
    """

    name: str
    format: str
    _parsed_data: Any

    def _require_structured(self) -> None:
        if self.format not in _STRUCTURED_FORMATS:
            raise UnstructuredFormatError(self.name, self.format)

    def _parse(self) -> Any:
        self._require_structured()
        if self._parsed_data is not _SENTINEL:
            return self._parsed_data

        raw = self._get_bytes()  # type: ignore[attr-defined]

        if self.format == "json":
            import json

            result = json.loads(raw)
        else:  # yaml
            import yaml

            result = yaml.safe_load(raw)

        self._parsed_data = result
        return result

    @property
    def data(self) -> Any:
        """Fully parsed dict/list. Lazy and memoised."""
        return self._parse()

    def get(self, path: str, *, default: Any = _SENTINEL) -> Any:
        """Dot/index path lookup.

        Raises :exc:`PropertyNotFoundError` if the path is not found and no
        ``default`` is supplied. ``default=None`` is valid and distinct from
        "no default".

        Examples::

            item.get("database.host")
            item.get("servers[0].port", default=8080)
        """
        parsed = self._parse()
        return path_get(parsed, path, default)

    def __getitem__(self, key: str | int) -> Any:
        return self._parse()[key]

    def __contains__(self, key: object) -> bool:
        return key in self._parse()
