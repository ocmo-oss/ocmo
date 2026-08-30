#!/usr/bin/env python3
"""Validate ocmo CLI commands and options against a live server.

Usage:
  OCMO_NAMESPACE=my-second-ns uv run python cli/scripts/validate_all.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass

import click

PASS = 0
FAIL = 0


@dataclass
class Case:
    desc: str
    args: list[str]
    expect_code: int = 0
    env: dict[str, str] | None = None
    check_stdout: Callable[[str], bool] | None = None
    check_stderr: Callable[[str], bool] | None = None


def run_ocmo(args: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    ocmo = os.environ.get("OCMO_BIN", os.path.join(os.path.dirname(__file__), "../../.venv/bin/ocmo"))
    run_env = os.environ.copy()
    if env is not None:
        for key, value in env.items():
            if value == "":
                run_env.pop(key, None)
            else:
                run_env[key] = value
    proc = subprocess.run(
        [ocmo, *args],
        capture_output=True,
        text=True,
        env=run_env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def record(case: Case) -> bool:
    global PASS, FAIL
    code, out, err = run_ocmo(case.args, env=case.env)
    ok = code == case.expect_code
    if ok and case.check_stdout and not case.check_stdout(out):
        ok = False
    if ok and case.check_stderr and not case.check_stderr(err):
        ok = False
    combined = out + err
    if ok:
        PASS += 1
        print(f"PASS [{code}] {case.desc}")
    else:
        FAIL += 1
        snippet = combined[:500].replace("\n", " ")
        print(f"FAIL [{code} expected {case.expect_code}] {case.desc}")
        print(f"  cmd: ocmo {' '.join(case.args)}")
        print(f"  out: {snippet}")
    return ok


def walk_commands(cmd: click.Command, prefix: list[str]) -> list[list[str]]:
    paths: list[list[str]] = []
    if isinstance(cmd, click.Group):
        for name, sub in sorted(cmd.commands.items()):
            paths.extend(walk_commands(sub, prefix + [name]))
    else:
        if prefix:
            paths.append(prefix)
    return paths


def help_has_option(help_text: str, opt: str) -> bool:
    return opt in help_text


def fetch_audit_object(ns: str) -> tuple[str, str] | None:
    code, out, err = run_ocmo(["-n", ns, "get", "audit", "-o", "json"])
    if code != 0:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    items = data if isinstance(data, list) else data.get("items", [])
    if not items:
        return None
    row = items[0]
    for candidate in items:
        otype = candidate.get("object_type") or candidate.get("objectType")
        oid = candidate.get("object_id") or candidate.get("objectId")
        if otype and otype not in ("namespace", "artifact") and oid:
            return str(oid), str(otype)
    oid = row.get("object_id") or row.get("objectId")
    otype = row.get("object_type") or row.get("objectType")
    if oid and otype:
        return str(oid), str(otype)
    return None


def main() -> int:
    global PASS, FAIL
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from ocmo_cli.main import cli

    ns = os.environ.get("OCMO_NAMESPACE", "my-second-ns")

    print(f"=== Help walk ({len(walk_commands(cli, []))} leaf commands) ===")
    for path in walk_commands(cli, []):
        code, _, _ = run_ocmo([*path, "--help"])
        if code != 0:
            FAIL += 1
            print(f"FAIL help {' '.join(path)}")
        else:
            PASS += 1

    audit_obj = fetch_audit_object(ns)

    print(f"=== Live smoke tests (namespace={ns}) ===")

    cases: list[Case] = [
        Case("version", ["version"]),
        Case("version --skip-server", ["version", "--skip-server"]),
        Case("whoami yaml", ["whoami", "-o", "yaml"], check_stdout=lambda s: "email" in s or "sub" in s),
        Case("config view", ["config", "view"]),
        Case("auth status", ["auth", "status"]),
        Case("completion bash", ["completion", "bash"], check_stdout=lambda s: "complete" in s.lower()),
        Case("can-i namespace:read", ["can-i", "namespace:read", "-n", ns]),
        Case("schema ocmo", ["schema", "ocmo"]),
        Case("schema config builtin", ["-n", ns, "schema", "config", "_permissions"]),
        Case("invalid global -o", ["-o", "blabla", "ls"], expect_code=2),
        Case("ls missing ns", ["ls"], expect_code=2, env={"OCMO_NAMESPACE": ""}),
        Case("api-health", ["api-health"]),
        Case("get cast name", ["get", "cast", "-o", "name"]),
        Case("get namespace list name", ["get", "namespace", "-o", "name"], check_stdout=lambda s: ns in s),
        Case("get namespace show", ["get", "namespace", ns, "-o", "yaml"], check_stdout=lambda s: ns in s),
        Case("ls root table", ["-n", ns, "ls"]),
        Case("ls name", ["-n", ns, "ls", "-o", "name"]),
        Case("ls path", ["-n", ns, "ls", "-o", "path"]),
        Case("ls json", ["-n", ns, "ls", "-o", "json"]),
        Case("tree", ["-n", ns, "tree"]),
        Case("search root q", ["-n", ns, "search", "tree", "--q", "git"]),
        Case("get item builtin", ["-n", ns, "get", "item", "_permissions", "-o", "name"]),
        Case("get item missing", ["-n", ns, "get", "item", "does-not-exist-xyz"], expect_code=3),
        Case("get lock list", ["-n", ns, "get", "lock", "-o", "name"]),
        Case("get audit list", ["-n", ns, "get", "audit", "-o", "name"]),
        Case("resolve builtin", ["-n", ns, "resolve", "_permissions", "--cast", "yaml"]),
        Case("resolve --trace-only", ["-n", ns, "resolve", "_permissions", "--trace-only", "-o", "yaml"]),
        Case("resolve parameters", ["-n", ns, "resolve", "parameters", "_permissions"]),
        Case("describe builtin", ["-n", ns, "describe", "_permissions"]),
        Case("diff missing", ["-n", ns, "diff", "does-not-exist"], expect_code=3),
        Case("export dry path", ["-n", ns, "export", "_permissions", "--to", "/tmp", "--dry-run"]),
        Case("create namespace dry-run", ["create", "namespace", "test-dry-cli", "--dry-run"]),
        Case("create config dry-run", ["-n", ns, "create", "config", "cli-val/test", "--dry-run"]),
        Case("tag dry-run", ["-n", ns, "tag", "item", "_permissions", "--tag", "cli-test-tag", "--dry-run"]),
        Case("propagate dry-run", ["-n", ns, "propagate", "config", "_permissions", "--dry-run"]),
        Case(
            "get namespace help has -o",
            ["get", "namespace", "--help"],
            check_stdout=lambda s: help_has_option(s, "--output"),
        ),
        Case(
            "get item help has --field", ["get", "item", "--help"], check_stdout=lambda s: help_has_option(s, "--field")
        ),
        Case(
            "search tree help has --q", ["search", "tree", "--help"], check_stdout=lambda s: help_has_option(s, "--q")
        ),
        Case(
            "create config help has -f",
            ["create", "config", "--help"],
            check_stdout=lambda s: help_has_option(s, "--file"),
        ),
    ]

    if audit_obj:
        oid, otype = audit_obj
        cases.append(
            Case(
                "timeline audit",
                ["-n", ns, "timeline", "audit", oid],
            )
        )
    else:
        print("SKIP timeline audit (no audit events in namespace)")

    for case in cases:
        record(case)

    for action in (
        "get",
        "create",
        "update",
        "delete",
        "move",
        "copy",
        "tag",
        "untag",
        "rotate",
        "propagate",
        "search",
        "timeline",
        "resolve-series",
    ):
        record(Case(f"group {action} help", [action, "--help"]))

    record(Case("resolve group help", ["resolve", "--help"]))

    print(f"\n=== Results: PASS={PASS} FAIL={FAIL} ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
