"""Pytest fixtures for OCMO resolve smoke tests."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from ocmo_smoke.bootstrap import bootstrap_case, grant_smoke_permissions
from ocmo_smoke.case import SmokeCase, discover_cases
from ocmo_smoke.client import OcmoApiClient

CASES_ROOT = Path(__file__).parent / "cases"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--base-url",
        action="store",
        default=os.environ.get("OCMO_SMOKE_BASE_URL", "http://localhost:8000"),
        help="OCMO API base URL (default: OCMO_SMOKE_BASE_URL or http://localhost:8000)",
    )
    parser.addoption(
        "--keep-namespace",
        action="store_true",
        default=os.environ.get("OCMO_SMOKE_KEEP_NAMESPACE", "").lower() in ("1", "true", "yes"),
        help="Do not delete the namespace after a test (for debugging)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "smoke: resolve API smoke tests")
    config.addinivalue_line(
        "markers",
        "content_types: document endpoints accept all OpenAPI content types",
    )


@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("--base-url")


@pytest.fixture(scope="session")
def keep_namespace(request: pytest.FixtureRequest) -> bool:
    return request.config.getoption("--keep-namespace")


@pytest.fixture(scope="session")
def api_client(base_url: str) -> OcmoApiClient:
    return OcmoApiClient(base_url)


@pytest.fixture(scope="session")
def all_cases() -> list[SmokeCase]:
    return discover_cases(CASES_ROOT)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "smoke_case" in metafunc.fixturenames:
        cases = discover_cases(CASES_ROOT)
        metafunc.parametrize(
            "smoke_case",
            cases,
            ids=[c.id for c in cases],
        )


@pytest.fixture
def smoke_namespace(
    api_client: OcmoApiClient,
    smoke_case: SmokeCase,
    keep_namespace: bool,
) -> str:
    """Create an isolated namespace, bootstrap the case tree, yield name, then delete."""

    ns_name = f"smoke-{smoke_case.id}-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    if created.status_code not in (200, 201):
        pytest.fail(
            f"Could not create namespace {ns_name!r}: HTTP {created.status_code}\n{created.text}"
        )

    try:
        grant_smoke_permissions(api_client, ns_name)
        bootstrap_case(api_client, ns_name, smoke_case)
    except Exception as exc:
        if not keep_namespace:
            api_client.delete_namespace(ns_name)
        pytest.fail(f"Bootstrap failed for case {smoke_case.id}: {exc}")

    yield ns_name

    if keep_namespace:
        print(f"\n[smoke] kept namespace for debugging: {ns_name}")
        return

    deleted = api_client.delete_namespace(ns_name)
    if deleted.status_code not in (200, 204) and deleted.status_code != 404:
        print(
            f"\n[smoke] warning: failed to delete namespace {ns_name}: "
            f"HTTP {deleted.status_code} {deleted.text}"
        )
