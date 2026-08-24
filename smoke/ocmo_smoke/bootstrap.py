"""Upload case tree fixtures into a namespace."""

from __future__ import annotations

import yaml

from .case import SmokeCase, iter_tree_files
from .client import ApiResponse, OcmoApiClient

_OCMO_METADATA_KEY = "_ocmo"


_SMOKE_OPEN_PERMISSIONS = """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "*"
    actions:
      - "*:*"
    resources:
      - "**"
"""


def grant_smoke_permissions(client: OcmoApiClient, namespace: str) -> None:
    """Replace default deny-all ``_permissions`` with open ABAC for smoke tests."""

    resp = client.update_config(namespace, "_permissions", _SMOKE_OPEN_PERMISSIONS)
    if not resp.ok:
        raise RuntimeError(
            f"Failed to set smoke permissions in namespace {namespace!r}: "
            f"HTTP {resp.status_code} {resp.text}"
        )


def _raise_create_failure(kind: str, tree_path: str, namespace: str, resp: ApiResponse) -> None:
    raise RuntimeError(
        f"Failed to create {kind} {tree_path!r} in namespace {namespace!r}: "
        f"HTTP {resp.status_code} {resp.text}"
    )


def _config_bootstrap_stub(contents: str) -> str:
    """YAML body without ``_ocmo`` for initial create when references form a cycle."""

    parsed = yaml.safe_load(contents) or {}
    if not isinstance(parsed, dict):
        return "placeholder: true\n"
    stub = {k: v for k, v in parsed.items() if k != _OCMO_METADATA_KEY}
    if not stub:
        stub = {"placeholder": True}
    return yaml.safe_dump(stub, default_flow_style=False, sort_keys=False)


def _bootstrap_configs(client: OcmoApiClient, namespace: str, configs: list[tuple[str, str]]) -> None:
    pending = list(configs)
    max_rounds = len(pending) + 1

    for _ in range(max_rounds):
        if not pending:
            return
        next_pending: list[tuple[str, str]] = []
        for tree_path, contents in pending:
            resp = client.create_config(namespace, tree_path, contents)
            if resp.ok:
                continue
            if resp.status_code == 422:
                next_pending.append((tree_path, contents))
                continue
            _raise_create_failure("config", tree_path, namespace, resp)

        if len(next_pending) == len(pending):
            for tree_path, contents in pending:
                stub = _config_bootstrap_stub(contents)
                created = client.create_config(namespace, tree_path, stub)
                if not created.ok:
                    _raise_create_failure("config", tree_path, namespace, created)
            for tree_path, contents in pending:
                updated = client.update_config(namespace, tree_path, contents)
                if not updated.ok:
                    raise RuntimeError(
                        f"Failed to update config {tree_path!r} in namespace {namespace!r}: "
                        f"HTTP {updated.status_code} {updated.text}"
                    )
            return
        pending = next_pending

    for tree_path, _contents in pending:
        raise RuntimeError(
            f"Could not create config {tree_path!r} in namespace {namespace!r} "
            f"after {max_rounds} attempts"
        )


def _create_ephemeral_item(
    client: OcmoApiClient, namespace: str, kind: str, path: str, data: str
) -> None:
    if kind == "secret":
        resp = client.create_secret(namespace, path, data)
    elif kind == "template":
        resp = client.create_template(namespace, path, data)
    else:
        raise ValueError(f"Unsupported ephemeral kind {kind!r}")
    if not resp.ok:
        _raise_create_failure(kind, path, namespace, resp)


def _delete_ephemeral_item(client: OcmoApiClient, namespace: str, path: str) -> None:
    resp = client.delete_item(namespace, path)
    if resp.status_code not in (200, 204, 404):
        raise RuntimeError(
            f"Failed to delete ephemeral item {path!r} in namespace {namespace!r}: "
            f"HTTP {resp.status_code} {resp.text}"
        )


def bootstrap_case(client: OcmoApiClient, namespace: str, case: SmokeCase) -> None:
    """Create all configs, templates, and secrets from the case directory."""

    ephemeral = case.bootstrap.ephemeral
    for item in ephemeral:
        _create_ephemeral_item(client, namespace, item.kind, item.path, item.data)

    configs: list[tuple[str, str]] = []

    try:
        for kind, tree_path, contents in iter_tree_files(case):
            if kind == "config":
                configs.append((tree_path, contents))
                continue

            if kind == "template":
                resp = client.create_template(namespace, tree_path, contents)
            elif kind == "secret":
                resp = client.create_secret(namespace, tree_path, contents)
            else:
                raise ValueError(f"Unknown kind {kind!r}")

            if not resp.ok:
                _raise_create_failure(kind, tree_path, namespace, resp)

        _bootstrap_configs(client, namespace, configs)
    finally:
        for item in reversed(ephemeral):
            _delete_ephemeral_item(client, namespace, item.path)
