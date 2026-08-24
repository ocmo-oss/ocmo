"""Bundled product NOTICE for the CLI (no API access required)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

LICENSE_NAME = "Apache License, Version 2.0"
LICENSE_SPDX = "Apache-2.0"
_NOTICE_PATH = Path(__file__).resolve().parents[1] / "NOTICE"


@lru_cache(maxsize=1)
def load_notice_text() -> str:
    if not _NOTICE_PATH.is_file():
        raise FileNotFoundError(f"NOTICE file not found: {_NOTICE_PATH}")
    return _NOTICE_PATH.read_text(encoding="utf-8").strip() + "\n"
