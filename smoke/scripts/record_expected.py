#!/usr/bin/env python3
"""Bootstrap a case into a throwaway namespace and write expected/ artifacts.

Usage (from smoke/ directory, API must be running):

    uv run python scripts/record_expected.py cases/simple_yaml
    uv run python scripts/record_expected.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ocmo_smoke.bootstrap import bootstrap_case  # noqa: E402
from ocmo_smoke.case import discover_cases, load_case  # noqa: E402
from ocmo_smoke.client import OcmoApiClient  # noqa: E402


def record_case(client: OcmoApiClient, case_dir: Path, base_url: str) -> None:
    case = load_case(case_dir)
    ns = f"record-{case.id}-{uuid.uuid4().hex[:8]}"
    print(f"Recording {case.id} → namespace {ns}")

    created = client.create_namespace(ns)
    if created.status_code not in (200, 201):
        raise SystemExit(f"create namespace failed: {created.text}")

    try:
        bootstrap_case(client, ns, case)
        resp = client.resolve(ns, case.resolve_path, case.query)
        if resp.status_code != case.expect.status:
            err_path = case.expected_dir / "error.json"
            case.expected_dir.mkdir(parents=True, exist_ok=True)
            err_path.write_text(
                json.dumps({"status": resp.status_code, "body": resp.body}, indent=2),
                encoding="utf-8",
            )
            print(f"  wrote {err_path} (non-{case.expect.status} response)")
            return

        body = resp.body
        case.expected_dir.mkdir(parents=True, exist_ok=True)

        if case.expect.trace_only:
            items = body.get("items") or []
            trace = items[0].get("trace") if items else body.get("trace", {})
            (case.expected_dir / "trace.json").write_text(
                json.dumps(trace, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print("  wrote expected/trace.json")
            return

        items = body.get("items") or []
        for idx, item in enumerate(items):
            url = item.get("url")
            if not url:
                print(f"  skip item {item.get('name')!r}: no url")
                continue
            content = client.download_artifact(url)
            # Prefer mapping from case.yaml expect.items
            if idx < len(case.expect.items):
                fname = case.expect.items[idx].file
            else:
                name = item.get("name", f"item-{idx}")
                safe = name.replace("/", "__")
                ext = ".json" if item.get("format") == "json" else ".yaml"
                if item.get("format") == "raw" and "." in safe:
                    ext = ""
                fname = safe + (ext if ext and not safe.endswith(ext) else "")

            out = case.expected_dir / fname
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(content)
            print(f"  wrote expected/{fname} ({len(content)} bytes)")
    finally:
        client.delete_namespace(ns)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_dir", nargs="?", help="Path to case folder")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    client = OcmoApiClient(args.base_url)
    if args.all:
        for case in discover_cases(ROOT / "cases"):
            record_case(client, case.root, args.base_url)
    elif args.case_dir:
        record_case(client, Path(args.case_dir).resolve(), args.base_url)
    else:
        parser.error("Provide case_dir or --all")


if __name__ == "__main__":
    main()
