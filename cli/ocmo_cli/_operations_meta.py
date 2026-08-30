"""Bundled operation metadata for SDK dispatch (scope, etc.)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, cast


@lru_cache(maxsize=1)
def load_operations_meta() -> dict[str, dict[str, Any]]:
    """Return per-operation metadata keyed by operation id.

    Uses the monorepo ``sdk/operations.yaml`` when present (local dev), otherwise
    the scope fields baked into ``_commands_map.OPERATIONS`` at build time.
    """
    monorepo = _try_load_monorepo_yaml()
    if monorepo:
        return monorepo

    from ocmo_cli._commands_map import OPERATIONS

    return {
        op_id: {"scope": cfg.get("scope", "namespace")}
        for op_id, cfg in OPERATIONS.items()
    }


def _try_load_monorepo_yaml() -> dict[str, dict[str, Any]] | None:
    ops_path = Path(__file__).resolve().parent.parent.parent / "sdk" / "operations.yaml"
    if not ops_path.exists():
        return None
    import yaml  # deferred

    with ops_path.open() as f:
        data = yaml.safe_load(f) or {}
    operations = data.get("operations")
    if not isinstance(operations, dict):
        return None
    return cast(dict[str, dict[str, Any]], operations)
