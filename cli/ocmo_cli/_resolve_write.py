"""Filesystem output for ``ocmo resolve``."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ._typing import ResolvedArtifact

WriteResult = Literal["created", "skipped", "rewritten", "failed"]


@dataclass(frozen=True)
class ResolveWriteOutcome:
    item: ResolvedArtifact
    path: Path
    result: WriteResult
    detail: str | None = None


def _absolute_path(path: Path) -> Path:
    return path.resolve()


def _outcome(
    item: ResolvedArtifact,
    dest: Path,
    result: WriteResult,
    detail: str | None = None,
) -> ResolveWriteOutcome:
    return ResolveWriteOutcome(item, _absolute_path(dest), result, detail)


def parse_checksum(checksum: str | None) -> tuple[str, str] | None:
    if not checksum:
        return None
    if ":" in checksum:
        algo, expected = checksum.split(":", 1)
        return algo, expected
    return "sha256", checksum


def digest_bytes(data: bytes, algo: str = "sha256") -> str:
    return hashlib.new(algo, data).hexdigest()


def _file_digest(path: Path, algo: str) -> str:
    return digest_bytes(path.read_bytes(), algo)


def file_matches_checksum(path: Path, checksum: str | None) -> bool:
    parsed = parse_checksum(checksum)
    if parsed is None or not path.is_file():
        return False
    algo, expected = parsed
    return _file_digest(path, algo) == expected


def _safe_join(base: Path, name: str) -> Path:
    if os.path.isabs(name):
        raise ValueError(f"Absolute path in server response: {name!r}")
    resolved = (base / name).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise ValueError(f"Path traversal detected: {name!r} escapes {base}")
    return base / name


def atomic_write(path: Path, data: bytes) -> None:
    tmp = Path(str(path) + ".tmp")
    try:
        with tmp.open("wb") as f:
            f.write(data)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def save_resolve_item(
    item: ResolvedArtifact,
    dest: Path,
    *,
    rewrite: bool,
    skip_existing: bool,
    data: bytes | None = None,
    skip_checksum: bool = False,
) -> ResolveWriteOutcome:
    """Save one resolved artifact with checksum-aware idempotency."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    checksum = None if skip_checksum else getattr(item, "checksum", None)

    if not skip_checksum and dest.is_file() and file_matches_checksum(dest, checksum):
        return _outcome(item, dest, "skipped", "unchanged")

    payload = data if data is not None else item.bytes

    if dest.is_file():
        if payload == dest.read_bytes():
            return _outcome(item, dest, "skipped", "unchanged")
        if skip_existing:
            return _outcome(item, dest, "skipped", "exists")
        if not rewrite:
            return _outcome(item, dest, "failed", "file exists and differs")
        atomic_write(dest, payload)
        return _outcome(item, dest, "rewritten")

    atomic_write(dest, payload)
    return _outcome(item, dest, "created")


def resolve_item_dest(
    item: ResolvedArtifact,
    *,
    output_file: str | None,
    output_dir: str,
) -> Path:
    if output_file:
        return Path(output_file)
    name = getattr(item, "name", None) or str(item)
    return _safe_join(Path(output_dir), name)


def write_resolve_items(
    items: Sequence[ResolvedArtifact],
    *,
    output_file: str | None = None,
    output_dir: str | None = None,
    rewrite: bool = False,
    skip_existing: bool = False,
    item_data: Callable[[ResolvedArtifact], tuple[bytes, bool]] | None = None,
) -> list[ResolveWriteOutcome]:
    if output_file and output_dir:
        raise ValueError("Specify only one of output_file or output_dir")
    if output_file:
        if len(items) != 1:
            raise ValueError("output_file requires exactly one resolved item")
        item = items[0]
        data, skip_checksum = _item_write_options(item, item_data)
        return [
            save_resolve_item(
                item,
                resolve_item_dest(item, output_file=output_file, output_dir="."),
                rewrite=rewrite,
                skip_existing=skip_existing,
                data=data,
                skip_checksum=skip_checksum,
            )
        ]

    if not output_dir:
        raise ValueError("output_dir is required when output_file is not set")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    outcomes: list[ResolveWriteOutcome] = []
    for item in items:
        data, skip_checksum = _item_write_options(item, item_data)
        dest = resolve_item_dest(item, output_file=None, output_dir=output_dir)
        outcomes.append(
            save_resolve_item(
                item,
                dest,
                rewrite=rewrite,
                skip_existing=skip_existing,
                data=data,
                skip_checksum=skip_checksum,
            )
        )
    return outcomes


def _item_write_options(
    item: ResolvedArtifact,
    item_data: Callable[[ResolvedArtifact], tuple[bytes, bool]] | None,
) -> tuple[bytes, bool]:
    if item_data is None:
        return item.bytes, False
    if not callable(item_data):
        raise TypeError("item_data must be callable")
    data, skip_checksum = item_data(item)
    return data, skip_checksum
