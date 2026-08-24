"""Live integration smoke tests for the OCMO CLI.

Self-contained live test flow:

1. Create a Global Permission rule granting ``read`` / ``write`` / ``delete`` on
   ``my-*`` namespaces for the authenticated principal.
2. Create ``my-smoke-<id>`` namespace, grant in-namespace tree access via
   ``_permissions``, and seed a minimal tree.
3. Exercise CLI commands against that namespace (read-only checks, then real
   mutating operations in a fixed order).
4. Delete the namespace and the Global Permission rule.

Run explicitly::

    OCMO_RUN_INTEGRATION=1 uv run pytest tests/test_smoke_integration.py -v
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from click.testing import Result

from ocmo_cli.main import cli
from tests.helpers import SmokeCli, SmokePaths

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        __import__("os").environ.get("OCMO_RUN_INTEGRATION") != "1",
        reason="Set OCMO_RUN_INTEGRATION=1 to run live API smoke tests",
    ),
]

_SOFT_OK = {0, 2}
_GP_MOVE_OK = {0, 2, 3, 4, 7}
_GP_NAMESPACE_PATTERN = "my-*"


def _with_yaml_file(session: SmokeCli, fn: Callable[[SmokeCli, str], Result]) -> Result:
    with session.runner.isolated_filesystem():
        Path("body.yaml").write_text("x: smoke\n", encoding="utf-8")
        return fn(session, "body.yaml")


def _latest_active_version(session: SmokeCli, path: str) -> int:
    result = session.ns_cmd("get", "version", path, "-o", "yaml")
    session.assert_ok(f"get version {path}", result)
    data = yaml.safe_load(result.output) or {}
    for entry in data.get("versions") or []:
        if not entry.get("deleted_at"):
            return int(entry["version"])
    pytest.fail(f"no active version found for {path!r}")


def _principal_email(session: SmokeCli) -> str:
    result = session.client("whoami", "-o", "yaml")
    session.assert_ok("whoami", result)
    data = yaml.safe_load(result.output) or {}
    user_details = data.get("user_details") or {}
    claims = user_details.get("claims") or {}
    email = user_details.get("email") or claims.get("email")
    if not email:
        pytest.fail(f"could not determine principal email from whoami: {result.output}")
    return str(email)


def _gp_rule_yaml(email: str) -> str:
    actor = {"kind": "User", "claims": {"email": email}}
    actors = [actor]
    rule = {
        "namespace": _GP_NAMESPACE_PATTERN,
        "description": "pytest CLI smoke (ephemeral)",
        "read": {"actors": actors},
        "write": {"actors": actors},
        "delete": {"actors": actors},
    }
    return yaml.safe_dump(rule, sort_keys=False)


def _build_read_namespace_cases(
    session: SmokeCli,
) -> list[tuple[str, Callable[[SmokeCli], Result], set[int]]]:
    ns = session.namespace
    p = session.paths
    return [
        (
            "can-i config:read",
            lambda s: s.client("can-i", "-n", ns, "config:read", "--resource", p.cfg),
            {0},
        ),
        ("get namespace show", lambda s: s.client("get", "namespace", ns, "-o", "yaml"), {0}),
        ("ls root", lambda s: s.ns_cmd("ls", p.root, "-o", "name"), {0}),
        ("tree root", lambda s: s.ns_cmd("tree", p.root), {0}),
        ("search tree", lambda s: s.ns_cmd("search", "tree", "--q", "smoke"), {0}),
        ("get item", lambda s: s.ns_cmd("get", "item", p.cfg, "-o", "name"), {0}),
        ("get version", lambda s: s.ns_cmd("get", "version", p.cfg, "-o", "name"), {0}),
        ("get audit list", lambda s: s.ns_cmd("get", "audit", "-o", "name"), {0}),
        ("get lock list", lambda s: s.ns_cmd("get", "lock", "-o", "name"), {0}),
        ("describe read", lambda s: s.ns_cmd("describe", p.cfg), {0}),
        (
            "resolve cast env",
            lambda s: s.ns_cmd("resolve", p.cfg, "--cast", "env", "--cast-option", "type=windows"),
            {0},
        ),
        ("resolve parameters", lambda s: s.ns_cmd("resolve", "parameters", p.cfg), {0}),
        ("resolve-series audit", lambda s: s.ns_cmd("resolve-series", "audit", p.cfg, "-o", "json"), {0}),
        ("timeline audit", lambda s: s.ns_cmd("timeline", "audit", p.cfg, "--limit", "5"), {0}),
        ("diff self", lambda s: s.ns_cmd("diff", p.cfg, p.cfg), {0}),
    ]


def _build_mutating_steps(
    session: SmokeCli,
) -> list[tuple[str, Callable[[SmokeCli], Result], set[int]]]:
    p = session.paths
    gp_id = session.gp_rule_id
    assert gp_id is not None
    export_dir = f"/tmp/ocmo-smoke-export-{session.namespace}"
    import_src = "/tmp/ocmo-smoke-import-src"
    cfg_version = _latest_active_version(session, p.cfg)

    def _edit_config(s: SmokeCli) -> Result:
        with s.runner.isolated_filesystem():
            editor = Path("editor.sh")
            editor.write_text('#!/bin/sh\nprintf "\\nsmoke_edited: true\\n" >> "$1"\n', encoding="utf-8")
            editor.chmod(0o755)
            return s.runner.invoke(
                cli,
                ["-n", s.namespace, "edit", "config", f"{p.root}/extra.yaml"],
                env={"EDITOR": str(editor.resolve())},
                catch_exceptions=False,
            )

    return [
        (
            "apply",
            lambda s: _with_yaml_file(
                s,
                lambda sess, path: sess.ns_cmd("apply", "-f", path, f"{p.root}/apply.yaml"),
            ),
            {0},
        ),
        (
            "create config",
            lambda s: _with_yaml_file(
                s,
                lambda sess, path: sess.ns_cmd("create", "config", f"{p.root}/extra.yaml", "-f", path),
            ),
            {0},
        ),
        (
            "update config",
            lambda s: _with_yaml_file(
                s,
                lambda sess, path: sess.ns_cmd("update", "config", f"{p.root}/extra.yaml", "-f", path),
            ),
            {0},
        ),
        (
            "describe write",
            lambda s: s.ns_cmd("describe", p.cfg, "--description", "smoke", "--yes"),
            {0},
        ),
        (
            "tag",
            lambda s: s.ns_cmd(
                "tag",
                "item",
                p.cfg,
                "--tag",
                "smoketag",
                "--version",
                str(cfg_version),
            ),
            {0},
        ),
        (
            "untag",
            lambda s: s.ns_cmd("untag", "item", p.cfg, "--tag", "smoketag"),
            {0},
        ),
        (
            "copy item",
            lambda s: s.ns_cmd("copy", "item", p.cfg, f"{p.root}/copied.yaml", "--yes"),
            {0},
        ),
        (
            "propagate config",
            lambda s: s.ns_cmd("propagate", "config", p.cfg, "--yes"),
            _SOFT_OK,
        ),
        (
            "resolve draft",
            lambda s: _with_yaml_file(
                s,
                lambda sess, path: sess.ns_cmd("resolve", "draft", p.cfg, "-f", path),
            ),
            {0},
        ),
        (
            "import",
            lambda s: s.ns_cmd("import", import_src, "--to", f"{p.root}/imported", "--yes"),
            _SOFT_OK,
        ),
        (
            "export",
            lambda s: s.ns_cmd("export", p.root, "--to", export_dir, "--overwrite"),
            {0},
        ),
        (
            "rotate token",
            lambda s: s.ns_cmd("rotate", "token", p.resolver, "--token-number", "1", "--yes"),
            {0},
        ),
        ("edit config", _edit_config, {0}),
        (
            "delete item preview",
            lambda s: s.ns_cmd("delete", "item", f"{p.root}/missing", "--preview"),
            {0, 3},
        ),
        (
            "delete item",
            lambda s: _with_yaml_file(
                s,
                lambda sess, path: (
                    sess.ns_cmd("apply", "-f", path, f"{p.root}/disposable.yaml"),
                    sess.ns_cmd("delete", "item", f"{p.root}/disposable.yaml", "--yes"),
                )[1],
            ),
            {0},
        ),
        (
            "move item",
            lambda s: _with_yaml_file(
                s,
                lambda sess, path: (
                    sess.ns_cmd("apply", "-f", path, f"{p.root}/move-me.yaml"),
                    sess.ns_cmd("move", "item", f"{p.root}/move-me.yaml", f"{p.root}/moved.yaml", "--yes"),
                )[1],
            ),
            {0},
        ),
        (
            "move globalpermission",
            lambda s: s.client("move", "globalpermission", gp_id, "--position", "1", "--yes"),
            _GP_MOVE_OK,
        ),
    ]


_READ_NAMESPACE_CASES = _build_read_namespace_cases(
    SmokeCli(namespace="my-smoke-placeholder", gp_rule_id="cli-smoke-gp-placeholder"),
)


_CLIENT_CASES: list[tuple[str, Callable[[SmokeCli], Result], set[int]]] = [
    ("version", lambda s: s.client("version"), {0}),
    ("whoami", lambda s: s.client("whoami"), {0}),
    ("api-health", lambda s: s.client("api-health"), {0}),
    ("auth status", lambda s: s.client("auth", "status"), {0}),
    ("config current-ns", lambda s: s.client("config", "current-ns"), {0}),
    ("config view", lambda s: s.client("config", "view"), {0}),
    ("completion bash", lambda s: s.client("completion", "bash"), {0}),
    ("get globalpermission", lambda s: s.client("get", "globalpermission"), {0}),
    ("get namespace list", lambda s: s.client("get", "namespace", "-o", "name"), {0}),
    ("get cast list", lambda s: s.client("get", "cast", "-o", "name"), {0}),
    ("get cast env", lambda s: s.client("get", "cast", "env", "-o", "name"), {0}),
    ("schema ocmo", lambda s: s.client("schema", "ocmo"), {0}),
    ("schema resolver", lambda s: s.client("schema", "resolver"), {0}),
]


def _namespace_permissions_yaml(email: str) -> str:
    rule = {
        "policies": [
            {
                "effect": "Allow",
                "actors": [{"kind": "User", "claims": {"email": email}}],
                "actions": ["*:*"],
                "resources": ["**"],
            }
        ]
    }
    return yaml.safe_dump(rule, sort_keys=False)


def _provision_session() -> SmokeCli:
    probe = SmokeCli(namespace="probe")
    whoami = probe.client("whoami")
    if whoami.exit_code != 0:
        pytest.skip(f"OCMO API unavailable: {whoami.output}")

    suffix = uuid.uuid4().hex[:12]
    gp_rule_id = f"cli-smoke-gp-{suffix}"
    ns_name = f"my-smoke-{suffix}"
    email = _principal_email(probe)

    with probe.runner.isolated_filesystem():
        Path("gp-rule.yaml").write_text(_gp_rule_yaml(email), encoding="utf-8")
        gp_created = probe.client("create", "globalpermission", gp_rule_id, "-f", "gp-rule.yaml")
    probe.assert_ok("create globalpermission", gp_created)

    ns_created = probe.client(
        "create",
        "namespace",
        ns_name,
        "--description",
        "pytest CLI smoke",
    )
    if ns_created.exit_code != 0:
        _delete_gp_rule(probe, gp_rule_id)
        detail = (ns_created.output + getattr(ns_created, "stderr", "")).strip()
        pytest.fail(f"cannot create namespace {ns_name!r}: {detail}")

    session = SmokeCli(
        namespace=ns_name,
        paths=SmokePaths.under("app"),
        gp_rule_id=gp_rule_id,
    )
    _seed_tree(session, email=email)
    return session


def _seed_tree(session: SmokeCli, *, email: str) -> None:
    import_dir = Path("/tmp/ocmo-smoke-import-src")
    import_dir.mkdir(parents=True, exist_ok=True)
    (import_dir / "test.yaml").write_text("x: smoke\n", encoding="utf-8")

    p = session.paths
    with session.runner.isolated_filesystem():
        Path("permissions.yaml").write_text(_namespace_permissions_yaml(email), encoding="utf-8")
        Path("cfg.yaml").write_text("hello: smoke\n", encoding="utf-8")
        Path("smoke.tpl").write_text("smoke template\n", encoding="utf-8")
        Path("resolver.yaml").write_text("{}\n", encoding="utf-8")

        for args in (
            ("apply", "-f", "permissions.yaml", "_permissions", "-t", "config"),
            ("apply", "-f", "cfg.yaml", p.cfg),
            ("apply", "-f", "smoke.tpl", p.template, "-t", "template"),
            ("apply", "-f", "resolver.yaml", p.resolver, "-t", "resolver"),
        ):
            result = session.ns_cmd(*args)
            session.assert_ok(f"seed {' '.join(args)}", result)


def _delete_gp_rule(session: SmokeCli, gp_rule_id: str) -> None:
    deleted = session.client("delete", "globalpermission", gp_rule_id, "--yes")
    if deleted.exit_code == 0:
        return
    gone = session.client("get", "globalpermission", gp_rule_id, "-o", "name")
    if gone.exit_code != 0:
        return
    combined = deleted.output + getattr(deleted, "stderr", "")
    pytest.fail(f"failed to delete global permission {gp_rule_id!r}: {combined}")


def _teardown(session: SmokeCli) -> None:
    if session.gp_rule_id is None:
        return

    deleted = session.client("delete", "namespace", session.namespace, "--yes")
    if deleted.exit_code != 0:
        gone = session.client("get", "namespace", session.namespace, "-o", "name")
        if gone.exit_code == 0:
            combined = deleted.output + getattr(deleted, "stderr", "")
            pytest.fail(f"failed to delete smoke namespace {session.namespace!r}: {combined}")

    _delete_gp_rule(session, session.gp_rule_id)


@pytest.fixture(scope="module")
def smoke() -> SmokeCli:
    session = _provision_session()
    try:
        yield session
    finally:
        _teardown(session)


@pytest.mark.parametrize(
    ("case_name", "allowed_exits"),
    [(name, allowed) for name, _, allowed in _READ_NAMESPACE_CASES],
    ids=[name for name, _, _ in _READ_NAMESPACE_CASES],
)
def test_smoke_namespace_read_command(
    case_name: str,
    allowed_exits: set[int],
    smoke: SmokeCli,
) -> None:
    cases = {name: fn for name, fn, _ in _build_read_namespace_cases(smoke)}
    result = cases[case_name](smoke)
    smoke.assert_ok(case_name, result, allow_exit=allowed_exits)


def test_smoke_namespace_mutating_commands(smoke: SmokeCli) -> None:
    """Run mutating namespace commands in a fixed order against disposable paths."""
    steps = _build_mutating_steps(smoke)
    for name, run, allowed in steps:
        result = run(smoke)
        smoke.assert_ok(name, result, allow_exit=allowed)


@pytest.mark.parametrize(
    ("case_name", "allowed_exits"),
    [(name, allowed) for name, _, allowed in _CLIENT_CASES],
    ids=[name for name, _, _ in _CLIENT_CASES],
)
def test_smoke_client_command(case_name: str, allowed_exits: set[int]) -> None:
    session = SmokeCli(namespace="probe")
    whoami = session.client("whoami")
    if whoami.exit_code != 0:
        pytest.skip(f"OCMO API unavailable: {whoami.output}")

    cases = {name: fn for name, fn, _ in _CLIENT_CASES}
    result = cases[case_name](session)
    session.assert_ok(case_name, result, allow_exit=allowed_exits)


def test_smoke_namespace_visible(smoke: SmokeCli) -> None:
    result = smoke.client("get", "namespace", smoke.namespace, "-o", "name")
    smoke.assert_ok("get smoke namespace", result)
    assert smoke.namespace in result.output


def test_smoke_gp_rule_visible(smoke: SmokeCli) -> None:
    assert smoke.gp_rule_id is not None
    result = smoke.client("get", "globalpermission", smoke.gp_rule_id, "-o", "yaml")
    smoke.assert_ok("get smoke gp rule", result)
    assert _GP_NAMESPACE_PATTERN in result.output
    assert smoke.gp_rule_id in result.output


def test_smoke_resolve_regression_guard(smoke: SmokeCli) -> None:
    result = smoke.ns_cmd("resolve", smoke.paths.cfg, "--cast", "yaml")
    smoke.assert_ok("resolve yaml", result)
    assert "hello" in result.output or "smoke" in result.output
