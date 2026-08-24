"""Pinned OpenAPI operation_id set — must match api/core/operation_ids.py and sdk/operations.yaml."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from django.test import SimpleTestCase

from core.operation_ids import ALL as API_OPERATION_IDS


def _openapi_operation_ids() -> set[str]:
    from ocmoapi.urls import api

    schema = api.get_openapi_schema()
    ids: set[str] = set()
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "operationId" in operation:
                ids.add(operation["operationId"])
    return ids


def _registry_operation_ids() -> set[str]:
    registry_path = Path(__file__).resolve().parents[3] / "sdk" / "operations.yaml"
    data = yaml.safe_load(registry_path.read_text())
    return set(data["operations"].keys())


class OperationIdRegistryTests(SimpleTestCase):
    def test_api_operation_ids_match_python_registry(self):
        self.assertEqual(_openapi_operation_ids(), API_OPERATION_IDS)

    def test_operations_yaml_matches_python_registry(self):
        self.assertEqual(_registry_operation_ids(), API_OPERATION_IDS)

    def test_openapi_snapshot_operation_ids_match_registry(self):
        snapshot_path = Path(__file__).resolve().parents[3] / "sdk" / "openapi.json"
        schema = json.loads(snapshot_path.read_text())
        ids: set[str] = set()
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    ids.add(operation["operationId"])
        self.assertEqual(ids, API_OPERATION_IDS)
