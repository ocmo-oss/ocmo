"""Address parsing tests."""

import pytest

from ocmo_cli._address import (
    AddressError,
    is_folder_address,
    parse_address,
    resolve_relocate_target,
    slug,
)


def test_simple_path() -> None:
    path, version = parse_address("app/web")
    assert path == "app/web"
    assert version is None


def test_path_with_version_suffix() -> None:
    path, version = parse_address("app/web@stable")
    assert path == "app/web"
    assert version == "stable"


def test_path_with_version_flag() -> None:
    path, version = parse_address("app/web", version_flag="3")
    assert path == "app/web"
    assert version == "3"


def test_conflict_raises() -> None:
    with pytest.raises(AddressError, match="Conflicting"):
        parse_address("app/web@stable", version_flag="latest")


def test_same_version_no_conflict() -> None:
    path, version = parse_address("app/web@stable", version_flag="stable")
    assert version == "stable"


def test_illegal_characters() -> None:
    with pytest.raises(AddressError):
        parse_address("app/web space")


def test_at_in_path_segment() -> None:
    # @ is always the version separator; "app/w@b/foo" → path="app/w", version="b/foo"
    path, version = parse_address("app/w@b/foo")
    assert path == "app/w"
    assert version == "b/foo"


def test_folder_address() -> None:
    assert is_folder_address("app/") is True
    assert is_folder_address("app/web") is False
    # "app/@stable" → path part is "app/" which ends with "/", so it IS a folder
    assert is_folder_address("app/@stable") is True


def test_uppercase_allowed() -> None:
    path, _ = parse_address("App/WebConfig")
    assert path == "App/WebConfig"


def test_slug_basic() -> None:
    assert slug("hello world") == "hello-world"
    assert slug("My App.conf") == "My-App.conf"
    assert slug("app_config") == "app_config"


def test_slug_preserves_case() -> None:
    assert slug("MyApp") == "MyApp"


def test_slug_trims_hyphens() -> None:
    assert slug("--foo--") == "foo"


def test_slug_multiple_replacements() -> None:
    assert slug("a b  c") == "a-b-c"


def test_resolve_relocate_target_exact_path() -> None:
    assert resolve_relocate_target("b/c/d", "a") == "a"


def test_resolve_relocate_target_into_directory() -> None:
    assert resolve_relocate_target("b/c/d", "a/") == "a/d"


def test_resolve_relocate_target_nested_directory() -> None:
    assert resolve_relocate_target("b/c/d", "x/y/") == "x/y/d"


def test_resolve_relocate_target_root_directory() -> None:
    assert resolve_relocate_target("b/c/d", "/") == "d"


def test_coverage_gate_commands_yaml() -> None:
    """Every operation in commands.yaml must have an entry (no MISSING/STALE)."""
    from pathlib import Path

    import yaml

    repo_root = Path(__file__).parent.parent.parent
    sdk_ops_path = repo_root / "sdk" / "operations.yaml"
    cli_ops_path = repo_root / "cli" / "commands.yaml"

    if not sdk_ops_path.exists() or not cli_ops_path.exists():
        pytest.skip("operations.yaml or commands.yaml not found")

    with sdk_ops_path.open() as f:
        sdk_ops = yaml.safe_load(f).get("operations", {})
    with cli_ops_path.open() as f:
        cli_ops = yaml.safe_load(f).get("operations", {})

    missing = [op for op in sdk_ops if op not in cli_ops]
    stale = [op for op in cli_ops if op not in sdk_ops]

    assert not missing, f"commands.yaml is missing entries: {missing}"
    assert not stale, f"commands.yaml has stale entries: {stale}"
