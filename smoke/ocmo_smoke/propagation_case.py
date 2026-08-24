"""Load propagation smoke case definitions from disk."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from .case import CASE_FILE, EXPECTED_DIR, _tree_path_from_file


@dataclass
class PropagationTargetExpect:
    path: str
    status: Optional[str] = None
    file: Optional[str] = None


@dataclass
class PropagationExpectSpec:
    status: int = 200
    error_substring: Optional[str] = None
    propagation: Optional[bool] = None
    targets: list[PropagationTargetExpect] = field(default_factory=list)


@dataclass
class PropagationCase:
    id: str
    root: Path
    source_path: str
    action: str  # propagate | tag | resolve
    propagate_version: str = "latest"
    tag_name: Optional[str] = None
    tag_version: Optional[int] = None
    resolve_path: Optional[str] = None
    resolve_query: dict[str, Any] = field(default_factory=dict)
    updates: list[tuple[str, str]] = field(default_factory=list)
    expect: PropagationExpectSpec = field(default_factory=PropagationExpectSpec)
    description: str = ""

    @property
    def configs_dir(self) -> Path:
        return self.root / "configs"

    @property
    def expected_dir(self) -> Path:
        return self.root / EXPECTED_DIR


def load_propagation_case(case_dir: Path) -> PropagationCase:
    meta_path = case_dir / CASE_FILE
    if not meta_path.is_file():
        raise ValueError(f"Missing {CASE_FILE} in {case_dir}")

    raw = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    if raw.get("kind") != "propagation":
        raise ValueError(f"Case {case_dir} is not a propagation case (kind != propagation)")

    expect_raw = raw.get("expect") or {}
    targets: list[PropagationTargetExpect] = []
    for item in expect_raw.get("targets") or []:
        if isinstance(item, str):
            targets.append(PropagationTargetExpect(path=item))
        else:
            targets.append(
                PropagationTargetExpect(
                    path=item["path"],
                    status=item.get("status"),
                    file=item.get("file"),
                )
            )

    tag_raw = raw.get("tag") or {}
    propagate_raw = raw.get("propagate") or {}
    updates: list[tuple[str, str]] = []
    for item in raw.get("updates") or []:
        updates.append((item["path"], item["file"]))

    return PropagationCase(
        id=raw.get("id") or case_dir.name,
        root=case_dir.resolve(),
        source_path=raw["source_path"],
        action=raw.get("action", "propagate"),
        propagate_version=str(propagate_raw.get("version", "latest")),
        tag_name=tag_raw.get("name"),
        tag_version=tag_raw.get("version"),
        resolve_path=raw.get("resolve_path"),
        resolve_query=dict(raw.get("query") or {}),
        updates=updates,
        expect=PropagationExpectSpec(
            status=int(expect_raw.get("status", 200)),
            error_substring=expect_raw.get("error_substring"),
            propagation=expect_raw.get("propagation"),
            targets=targets,
        ),
        description=raw.get("description", ""),
    )


def discover_propagation_cases(cases_root: Path) -> list[PropagationCase]:
    cases: list[PropagationCase] = []
    if not cases_root.is_dir():
        return cases
    for path in sorted(cases_root.iterdir()):
        if not path.is_dir():
            continue
        meta = path / CASE_FILE
        if not meta.is_file():
            continue
        raw = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        if raw.get("kind") == "propagation":
            cases.append(load_propagation_case(path))
    return cases


def iter_propagation_configs(case: PropagationCase) -> list[tuple[str, str]]:
    """Yield ``(tree_path, contents)`` for config fixtures only."""

    out: list[tuple[str, str]] = []
    configs_dir = case.configs_dir
    if not configs_dir.is_dir():
        return out
    for path in sorted(configs_dir.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        tree_path = _tree_path_from_file(configs_dir, path)
        out.append((tree_path, path.read_text(encoding="utf-8")))
    return out
