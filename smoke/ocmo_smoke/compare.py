"""Compare resolved artifacts to expected files with readable diffs."""

from __future__ import annotations

import difflib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ResolvedArtifact:
    name: str
    format: str
    content: bytes
    trace: dict[str, Any]
    url: Optional[str] = None
    checksum: Optional[str] = None


def normalize_text(content: bytes, *, strip_trailing_newline: bool = True) -> str:
    text = content.decode("utf-8").replace("\r\n", "\n")
    if strip_trailing_newline:
        text = text.rstrip("\n")
        text = text + "\n"
    return text


def read_expected_file(path: Path) -> bytes:
    return path.read_bytes()


def unified_diff(
    expected: str,
    actual: str,
    *,
    fromfile: str,
    tofile: str,
    context: int = 3,
) -> str:
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
            n=context,
        )
    )


def assert_text_equal(
    expected_path: Path,
    actual_content: bytes,
    *,
    item_name: str,
    strip_trailing_newline: bool = True,
) -> None:
    expected_bytes = read_expected_file(expected_path)
    expected_text = normalize_text(expected_bytes, strip_trailing_newline=strip_trailing_newline)
    actual_text = normalize_text(actual_content, strip_trailing_newline=strip_trailing_newline)

    if expected_text == actual_text:
        return

    diff = unified_diff(
        expected_text,
        actual_text,
        fromfile=f"expected/{expected_path.name}",
        tofile=f"actual/{item_name}",
    )
    raise AssertionError(
        f"Resolved content mismatch for item {item_name!r}\n"
        f"  expected file: {expected_path}\n"
        f"{diff or '(no diff lines produced)'}"
    )


def assert_json_equal(
    expected_path: Path,
    actual_content: bytes,
    *,
    item_name: str,
) -> None:
    expected_obj = json.loads(expected_path.read_text(encoding="utf-8"))
    actual_obj = json.loads(actual_content.decode("utf-8"))
    if expected_obj == actual_obj:
        return

    expected_str = json.dumps(expected_obj, indent=2, sort_keys=True) + "\n"
    actual_str = json.dumps(actual_obj, indent=2, sort_keys=True) + "\n"
    diff = unified_diff(
        expected_str,
        actual_str,
        fromfile=f"expected/{expected_path.name}",
        tofile=f"actual/{item_name}",
    )
    raise AssertionError(
        f"Resolved JSON mismatch for item {item_name!r}\n"
        f"  expected file: {expected_path}\n"
        f"{diff}"
    )


def compare_item_to_file(
    expected_path: Path,
    artifact: ResolvedArtifact,
    *,
    strip_trailing_newline: bool = True,
) -> None:
    if artifact.name and expected_path.suffix == ".json":
        assert_json_equal(expected_path, artifact.content, item_name=artifact.name)
    elif expected_path.suffix == ".json":
        assert_json_equal(expected_path, artifact.content, item_name=artifact.name or expected_path.name)
    else:
        assert_text_equal(
            expected_path,
            artifact.content,
            item_name=artifact.name or expected_path.name,
            strip_trailing_newline=strip_trailing_newline,
        )


def assert_multiset_files_equal(
    expected_dir: Path,
    expected_files: list[str],
    artifacts: list[ResolvedArtifact],
) -> None:
    """Compare resolved outputs as a multiset (order and names may differ)."""

    expected_pairs = [
        (f, normalize_text(read_expected_file(expected_dir / f))) for f in expected_files
    ]
    actual_pairs = [(a.name, normalize_text(a.content)) for a in artifacts]

    if Counter(text for _, text in expected_pairs) != Counter(
        text for _, text in actual_pairs
    ):
        lines = [
            "Multiset content mismatch:",
            f"  expected {len(expected_pairs)} file(s), got {len(actual_pairs)} artifact(s)",
            "",
            "Actual artifacts:",
        ]
        for name, text in actual_pairs:
            preview = text.splitlines()[0] if text else "(empty)"
            lines.append(f"  {name!r}: {preview!r} ({len(text)} chars)")
        lines.append("")
        lines.append("Expected files:")
        for fname, text in expected_pairs:
            preview = text.splitlines()[0] if text else "(empty)"
            lines.append(f"  {fname}: {preview!r} ({len(text)} chars)")

        exp_counter = Counter(text for _, text in expected_pairs)
        for fname, exp_text in expected_pairs:
            if exp_counter[exp_text] > Counter(text for _, text in actual_pairs)[exp_text]:
                act_name, act_text = actual_pairs[0]
                for an, at in actual_pairs:
                    if at != exp_text:
                        act_name, act_text = an, at
                        break
                lines.append("")
                lines.append(
                    unified_diff(
                        exp_text,
                        act_text,
                        fromfile=f"expected/{fname}",
                        tofile=f"actual/{act_name}",
                    )
                )
                break

        raise AssertionError("\n".join(lines))


def assert_trace_equal(expected_path: Path, actual_trace: dict[str, Any]) -> None:
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if expected == actual_trace:
        return
    diff = unified_diff(
        json.dumps(expected, indent=2, sort_keys=True) + "\n",
        json.dumps(actual_trace, indent=2, sort_keys=True) + "\n",
        fromfile="expected/trace.json",
        tofile="actual/trace",
    )
    raise AssertionError(f"Trace mismatch\n{diff}")
