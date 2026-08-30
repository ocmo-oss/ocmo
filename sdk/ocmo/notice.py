"""Bundled product NOTICE and license metadata (no API access required)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from . import _version

PRODUCT = "ocmo"
LICENSE_NAME = "Apache License, Version 2.0"
LICENSE_SPDX = "Apache-2.0"
_PACKAGE_NOTICE_PATH = Path(__file__).resolve().parent / "NOTICE"
_COMPONENT_NOTICE_PATH = Path(__file__).resolve().parents[1] / "NOTICE"


def _notice_paths() -> tuple[Path, ...]:
    return (_PACKAGE_NOTICE_PATH, _COMPONENT_NOTICE_PATH)


@lru_cache(maxsize=1)
def load_notice_text() -> str:
    for path in _notice_paths():
        if path.is_file():
            return path.read_text(encoding="utf-8").strip() + "\n"
    raise FileNotFoundError(f"NOTICE file not found; searched: {', '.join(str(p) for p in _notice_paths())}")


def product_version_info(*, include_notice: bool = False) -> dict[str, Any]:
    """Return local product metadata shipped with the SDK."""
    info: dict[str, Any] = {
        "product": PRODUCT,
        "version": _version.__version__,
        "license": LICENSE_SPDX,
        "license_name": LICENSE_NAME,
    }
    if include_notice:
        info["notice"] = load_notice_text()
    return info
