"""Shared typing helpers for Click decorators and deferred SDK imports."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeAlias, TypeVar

ClickDecorator: TypeAlias = Callable[[Callable[..., Any]], Callable[..., Any]]

F = TypeVar("F", bound=Callable[..., Any])


class ResolvedArtifact(Protocol):
    name: str | None
    version: int | None
    format: str | None
    checksum: str | None
    trace: dict[str, Any]
    url: str | None

    @property
    def bytes(self) -> bytes: ...

    @property
    def text(self) -> str: ...

    def get(self, path: str, *, default: Any = ...) -> Any: ...
