"""Smoke tests for change requests (~change-requests/ API)."""

from __future__ import annotations

import uuid

import pytest

from ocmo_smoke.bootstrap import grant_smoke_permissions
from ocmo_smoke.client import OcmoApiClient

_CONFIG_PATH = "app/cfg"


def _item_document_text(body: dict) -> str:
    version_data = body.get("version_data")
    if isinstance(version_data, dict):
        data = version_data.get("data")
        if isinstance(data, str):
            return data
    for key in ("content", "data"):
        value = body.get(key)
        if isinstance(value, str):
            return value
    return ""


def _enable_change_requests(
    client: OcmoApiClient,
    namespace: str,
    *,
    required_approvals: int = 0,
) -> None:
    resp = client.patch_namespace(
        namespace,
        {
            "change_requests_enabled": True,
            "change_requests_required_approvals": required_approvals,
        },
    )
    assert resp.status_code == 200, resp.text


@pytest.fixture
def cr_namespace(api_client: OcmoApiClient) -> str:
    ns_name = f"smoke-cr-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    assert created.status_code in (200, 201), created.text
    grant_smoke_permissions(api_client, ns_name)
    _enable_change_requests(api_client, ns_name, required_approvals=0)
    assert api_client.create_config(
        ns_name, _CONFIG_PATH, b"key: v1\n"
    ).status_code in (200, 201)
    yield ns_name
    api_client.delete_namespace(ns_name)


@pytest.fixture
def cr_namespace_with_approvals(api_client: OcmoApiClient) -> str:
    ns_name = f"smoke-cr-appr-{uuid.uuid4().hex[:8]}"
    created = api_client.create_namespace(ns_name)
    assert created.status_code in (200, 201), created.text
    grant_smoke_permissions(api_client, ns_name)
    _enable_change_requests(api_client, ns_name, required_approvals=1)
    assert api_client.create_config(
        ns_name, _CONFIG_PATH, b"key: v1\n"
    ).status_code in (200, 201)
    yield ns_name
    api_client.delete_namespace(ns_name)


def _create_open_cr(
    client: OcmoApiClient, namespace: str, body: bytes = b"key: cr-draft\n"
) -> int:
    created = client.create_change_request(
        namespace,
        _CONFIG_PATH,
        title="Smoke CR",
        body=body,
    )
    assert created.status_code == 201, created.text
    return int(created.body["number"])


@pytest.mark.smoke
def test_change_requests_disabled_returns_404(
    api_client: OcmoApiClient,
) -> None:
    ns_name = f"smoke-cr-off-{uuid.uuid4().hex[:8]}"
    assert api_client.create_namespace(ns_name).status_code in (200, 201)
    grant_smoke_permissions(api_client, ns_name)
    assert api_client.create_config(
        ns_name, _CONFIG_PATH, b"key: v1\n"
    ).status_code in (200, 201)

    resp = api_client.get_change_request(ns_name, _CONFIG_PATH, 1)
    assert resp.status_code == 404, resp.text
    api_client.delete_namespace(ns_name)


@pytest.mark.smoke
def test_create_get_and_list_change_request(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace)

    got = api_client.get_change_request(cr_namespace, _CONFIG_PATH, number)
    assert got.status_code == 200, got.text
    assert got.body["status"] == "open"
    assert got.body["title"] == "Smoke CR"

    listed = api_client.list_change_requests(
        cr_namespace, path=_CONFIG_PATH, status="open"
    )
    assert listed.status_code == 200, listed.text
    numbers = {item["number"] for item in listed.body["items"]}
    assert number in numbers


@pytest.mark.smoke
def test_read_cr_content_via_item_ref(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    _create_open_cr(api_client, cr_namespace, body=b"key: via-ref\n")
    item = api_client.get_item(cr_namespace, _CONFIG_PATH, version="~1")
    assert item.status_code == 200, item.text
    assert "via-ref" in _item_document_text(item.body)


@pytest.mark.smoke
def test_update_and_patch_metadata(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace)

    updated = api_client.update_change_request(
        cr_namespace,
        _CONFIG_PATH,
        number,
        b"key: updated-body\n",
    )
    assert updated.status_code == 200, updated.text

    patched = api_client.patch_change_request_metadata(
        cr_namespace,
        _CONFIG_PATH,
        number,
        {"title": "Renamed CR"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.body["title"] == "Renamed CR"


@pytest.mark.smoke
def test_diff_against_base(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace, body=b"key: diff-me\n")
    diff = api_client.diff_change_request(
        cr_namespace, _CONFIG_PATH, number, against="base", reveal=True
    )
    assert diff.status_code == 200, diff.text
    assert diff.body["to_side"]["requested"] == f"~{number}"
    assert "diff-me" in diff.body["to_side"]["data"]
    assert diff.body["identical"] is False


@pytest.mark.smoke
def test_apply_without_required_approvals(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace, body=b"key: merged\n")
    applied = api_client.apply_change_request(cr_namespace, _CONFIG_PATH, number)
    assert applied.status_code == 200, applied.text
    assert applied.body["status"] == "applied"
    assert applied.body["applied_version"] == 2

    latest = api_client.get_item(cr_namespace, _CONFIG_PATH)
    assert latest.status_code == 200, latest.text
    assert "merged" in _item_document_text(latest.body)


@pytest.mark.smoke
def test_apply_requires_approval_when_configured(
    api_client: OcmoApiClient, cr_namespace_with_approvals: str
) -> None:
    ns = cr_namespace_with_approvals
    number = _create_open_cr(api_client, ns, body=b"key: needs-approval\n")
    blocked = api_client.apply_change_request(ns, _CONFIG_PATH, number)
    assert blocked.status_code == 409, blocked.text


@pytest.mark.smoke
def test_author_cannot_approve_own_change_request(
    api_client: OcmoApiClient, cr_namespace_with_approvals: str
) -> None:
    ns = cr_namespace_with_approvals
    number = _create_open_cr(api_client, ns)
    resp = api_client.approve_change_request(ns, _CONFIG_PATH, number)
    assert resp.status_code == 409, resp.text


@pytest.mark.smoke
def test_reject_change_request(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace)
    rejected = api_client.reject_change_request(
        cr_namespace, _CONFIG_PATH, number, reason="Not now"
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.body["status"] == "rejected"
    assert rejected.body["rejected_reason"] == "Not now"


@pytest.mark.smoke
def test_withdraw_change_request(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace)
    withdrawn = api_client.withdraw_change_request(cr_namespace, _CONFIG_PATH, number)
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.body["status"] == "withdrawn"


@pytest.mark.smoke
def test_auto_reject_open_cr_on_new_version(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace)
    assert (
        api_client.update_config(cr_namespace, _CONFIG_PATH, b"key: v2\n").status_code
        == 200
    )

    got = api_client.get_change_request(cr_namespace, _CONFIG_PATH, number)
    assert got.status_code == 200, got.text
    assert got.body["status"] == "rejected"
    assert got.body["rejected_reason"] == "new_version_published"


@pytest.mark.smoke
def test_comment_create_and_list(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace)
    created = api_client.create_change_request_comment(
        cr_namespace, _CONFIG_PATH, number, "Please review"
    )
    assert created.status_code == 201, created.text

    listed = api_client.list_change_request_comments(
        cr_namespace, _CONFIG_PATH, number
    )
    assert listed.status_code == 200, listed.text
    bodies = [c["body"] for c in listed.body["items"]]
    assert "Please review" in bodies


@pytest.mark.smoke
def test_apply_blocked_under_lock(
    api_client: OcmoApiClient, cr_namespace: str
) -> None:
    number = _create_open_cr(api_client, cr_namespace, body=b"key: locked\n")
    assert api_client.create_lock(cr_namespace, "app", "freeze").status_code == 201

    blocked = api_client.apply_change_request(cr_namespace, _CONFIG_PATH, number)
    assert blocked.status_code == 423, blocked.text
