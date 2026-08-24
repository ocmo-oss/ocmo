"""Product version resolved once at process startup."""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

PRODUCT = "ocmo"
_PACKAGE_NAME = "ocmo-api"


def _read_pyproject_version() -> str:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    return data["project"]["version"]


def _resolve_ocmo_version() -> str:
    try:
        return importlib.metadata.version(_PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return _read_pyproject_version()


VERSION = _resolve_ocmo_version()
