"""operations.yaml must stay aligned with the committed OpenAPI snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = ROOT / "operations.yaml"
OPENAPI = ROOT / "openapi.json"


def _openapi_ids() -> set[str]:
    schema = json.loads(OPENAPI.read_text())
    ids: set[str] = set()
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "operationId" in operation:
                ids.add(operation["operationId"])
    return ids


def test_operations_yaml_covers_openapi_snapshot():
    registry = yaml.safe_load(OPERATIONS.read_text())["operations"]
    assert set(registry.keys()) == _openapi_ids()


def test_sdk_false_operations_are_documented_skips():
    registry = yaml.safe_load(OPERATIONS.read_text())["operations"]
    assert registry["resolve_config"]["sdk"] is False
    assert registry["download_resolved_artifact"]["sdk"] is False
