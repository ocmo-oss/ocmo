"""Load smoke case definitions and tree fixtures from disk."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


CASE_FILE = "case.yaml"
TREE_DIRS = ("configs", "templates", "secrets")
EXPECTED_DIR = "expected"


@dataclass
class ExpectedItem:
    """One resolved output artifact to compare."""

    file: str  # path under expected/
    name: Optional[str] = None  # optional API item name assertion


@dataclass
class EphemeralBootstrapItem:
    """Temporary tree item created only to pass save-time reference checks."""

    kind: str  # secret | template
    path: str
    data: str


@dataclass
class BootstrapSpec:
    ephemeral: list[EphemeralBootstrapItem] = field(default_factory=list)


@dataclass
class ExpectSpec:
    status: int = 200
    items: list[ExpectedItem] = field(default_factory=list)
    error_substring: Optional[str] = None
    trace_only: bool = False
    sort_by_name: bool = False
    match: str = "ordered"  # ordered | multiset


@dataclass
class SmokeCase:
    id: str
    root: Path
    resolve_path: str
    query: dict[str, Any]
    expect: ExpectSpec
    bootstrap: BootstrapSpec = field(default_factory=BootstrapSpec)
    description: str = ""

    @property
    def configs_dir(self) -> Path:
        return self.root / "configs"

    @property
    def templates_dir(self) -> Path:
        return self.root / "templates"

    @property
    def secrets_dir(self) -> Path:
        return self.root / "secrets"

    @property
    def expected_dir(self) -> Path:
        return self.root / EXPECTED_DIR


def _tree_path_from_file(base: Path, file_path: Path) -> str:
    """Map fixture file path to OCMO tree path.

    Config/secret YAML files drop ``.yaml`` / ``.yml`` (``configs/a/b.yaml`` → ``a/b``).
    Templates and other extensions keep the full filename
    (``templates/x/nginx.conf.j2`` → ``x/nginx.conf.j2``).
    """

    rel = file_path.relative_to(base)
    parts = list(rel.parts)
    last = parts[-1]
    if last.endswith((".yaml", ".yml")):
        parts[-1] = last.rsplit(".", 1)[0]
    return "/".join(parts)


def iter_tree_files(case: SmokeCase) -> list[tuple[str, str, str]]:
    """Yield ``(kind, tree_path, file_contents)`` for bootstrap.

    Order: secrets, templates, then configs (so save-time ``_ocmo`` reference
    checks succeed when dependencies are uploaded first).
    """

    out: list[tuple[str, str, str]] = []
    for kind, directory in (
        ("secret", case.secrets_dir),
        ("template", case.templates_dir),
        ("config", case.configs_dir),
    ):
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            tree_path = _tree_path_from_file(directory, path)
            out.append((kind, tree_path, path.read_text(encoding="utf-8")))
    return out


def load_case(case_dir: Path) -> SmokeCase:
    meta_path = case_dir / CASE_FILE
    if not meta_path.is_file():
        raise ValueError(f"Missing {CASE_FILE} in {case_dir}")

    raw = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    case_id = raw.get("id") or case_dir.name
    resolve_path = raw["resolve_path"]
    query = raw.get("query") or {}

    expect_raw = raw.get("expect") or {}
    items: list[ExpectedItem] = []
    for item in expect_raw.get("items") or []:
        if isinstance(item, str):
            items.append(ExpectedItem(file=item))
        else:
            items.append(
                ExpectedItem(
                    file=item["file"],
                    name=item.get("name"),
                )
            )

    expect = ExpectSpec(
        status=int(expect_raw.get("status", 200)),
        items=items,
        error_substring=expect_raw.get("error_substring"),
        trace_only=bool(expect_raw.get("trace_only", False)),
        sort_by_name=bool(expect_raw.get("sort_by_name", False)),
        match=str(expect_raw.get("match", "ordered")),
    )

    bootstrap_raw = raw.get("bootstrap") or {}
    ephemeral: list[EphemeralBootstrapItem] = []
    for item in bootstrap_raw.get("ephemeral") or []:
        ephemeral.append(
            EphemeralBootstrapItem(
                kind=item["kind"],
                path=item["path"],
                data=item.get("data", "placeholder: true\n"),
            )
        )

    return SmokeCase(
        id=case_id,
        root=case_dir.resolve(),
        resolve_path=resolve_path,
        query=query,
        expect=expect,
        bootstrap=BootstrapSpec(ephemeral=ephemeral),
        description=raw.get("description", ""),
    )


def discover_cases(cases_root: Path) -> list[SmokeCase]:
    cases: list[SmokeCase] = []
    if not cases_root.is_dir():
        return cases
    for path in sorted(cases_root.iterdir()):
        meta = path / CASE_FILE
        if not path.is_dir() or not meta.is_file():
            continue
        raw = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        if raw.get("kind") == "propagation":
            continue
        cases.append(load_case(path))
    return cases
