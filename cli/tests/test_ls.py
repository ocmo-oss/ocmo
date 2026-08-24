"""Tests for ocmo ls / tree navigation output."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import click
import pytest

from ocmo_cli._ls_wide import (
    basic_ls_row,
    enrich_ls_rows,
    format_permission_string,
    probe_operations_for_node,
    sort_wide_rows,
)
from ocmo_cli._output_manifest import get_command_spec, validate_output_format
from ocmo_cli.commands.ls import (
    _DEFAULT_BUILTIN_NAMESPACE_PATHS,
    _build_tree_hierarchy,
    _filter_navigate_data,
    _filter_navigation_rows,
    _load_system_paths,
    _navigation_rows,
    _render_plain_tree,
    _tree_node_label,
    _validate_ls_sort,
)


def test_filter_folders_removes_folder_nodes():
    rows = [
        {"path": "app", "node_type": "folder"},
        {"path": "app/web", "node_type": "config"},
    ]
    assert _filter_navigation_rows(
        rows,
        hide_folders=True,
        hide_system=False,
        system_paths=frozenset(),
    ) == [{"path": "app/web", "node_type": "config"}]


def test_filter_system_paths_removes_builtin_items():
    rows = [
        {"path": "_permissions", "node_type": "config"},
        {"path": "app/web", "node_type": "config"},
    ]
    assert _filter_navigation_rows(
        rows,
        hide_folders=False,
        hide_system=True,
        system_paths=_DEFAULT_BUILTIN_NAMESPACE_PATHS,
    ) == [{"path": "app/web", "node_type": "config"}]


def test_load_system_paths_from_version_info():
    client = MagicMock()
    client.version_info.return_value = {
        "builtin_namespace_paths": {
            "order": ["_permissions", "_webhooks"],
        },
    }
    assert _load_system_paths(client) == frozenset({"_permissions", "_webhooks"})


def test_filter_navigate_data_hides_folders_in_json_payload():
    data = {
        "item": {"path": "app", "node_type": "folder"},
        "children": [
            {"path": "app", "node_type": "folder"},
            {"path": "app/web", "node_type": "config"},
        ],
        "children_count": 2,
        "is_leaf": False,
        "breadcrumbs": [],
    }
    payload = _filter_navigate_data(
        data,
        hide_folders=True,
        hide_system=False,
        system_paths=frozenset(),
    )
    assert payload["children"] == [{"path": "app/web", "node_type": "config"}]
    assert payload["children_count"] == 1


def test_filter_navigate_data_hides_system_items_in_json_payload():
    data = {
        "item": None,
        "children": [
            {"path": "_permissions.schema", "node_type": "config"},
            {"path": "app/web", "node_type": "config"},
        ],
        "children_count": 2,
        "is_leaf": False,
        "breadcrumbs": [],
    }
    payload = _filter_navigate_data(
        data,
        hide_folders=False,
        hide_system=True,
        system_paths=_DEFAULT_BUILTIN_NAMESPACE_PATHS,
    )
    assert payload["children"] == [{"path": "app/web", "node_type": "config"}]
    assert payload["children_count"] == 1


def test_ls_manifest_rejects_raw() -> None:
    spec = get_command_spec("ls")
    with pytest.raises(click.BadParameter):
        validate_output_format("raw", spec)


def test_validate_ls_sort_requires_wide():
    with pytest.raises(SystemExit):
        _validate_ls_sort("type", None)
    with pytest.raises(SystemExit):
        _validate_ls_sort("updated", "table")
    _validate_ls_sort("path", "wide")
    _validate_ls_sort(None, "table")


def test_build_tree_hierarchy_nests_flat_recursive_rows() -> None:
    rows = [
        {"path": "a", "name": "a", "node_type": "folder"},
        {"path": "a/confT", "name": "confT", "node_type": "config"},
        {"path": "b", "name": "b", "node_type": "folder"},
        {"path": "b/c", "name": "c", "node_type": "folder"},
        {"path": "b/c/confT", "name": "confT", "node_type": "config"},
    ]
    tree = _build_tree_hierarchy(rows)
    assert [node["path"] for node in tree] == ["a", "b"]
    assert [child["path"] for child in tree[0]["children"]] == ["a/confT"]
    assert [child["path"] for child in tree[1]["children"]] == ["b/c"]
    assert tree[1]["children"][0]["children"][0]["path"] == "b/c/confT"


def test_build_tree_hierarchy_uses_address_as_root_prefix() -> None:
    rows = [
        {"path": "app/web", "name": "web", "node_type": "folder"},
        {"path": "app/web/index.conf", "name": "index.conf", "node_type": "config"},
        {"path": "app/api", "name": "api", "node_type": "config"},
    ]
    tree = _build_tree_hierarchy(rows, root_prefix="app")
    assert [node["path"] for node in tree] == ["app/api", "app/web"]
    assert tree[1]["children"][0]["path"] == "app/web/index.conf"


def test_render_plain_tree_shows_nested_branches(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _build_tree_hierarchy(
        [
            {"path": "a", "name": "a", "node_type": "folder"},
            {"path": "a/confT", "name": "confT", "node_type": "config"},
            {"path": "b", "name": "b", "node_type": "folder"},
        ]
    )
    _render_plain_tree(tree, prefix="", connector="")
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "├── a  [folder]"
    assert out[1].startswith("│   ")
    assert "confT" in out[1]
    assert out[-1] == "└── b  [folder]"


def test_render_plain_tree_respects_depth(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _build_tree_hierarchy(
        [
            {"path": "a", "name": "a", "node_type": "folder"},
            {"path": "a/confT", "name": "confT", "node_type": "config"},
            {"path": "b", "name": "b", "node_type": "folder"},
            {"path": "b/c", "name": "c", "node_type": "folder"},
            {"path": "b/c/confT", "name": "confT", "node_type": "config"},
        ]
    )
    _render_plain_tree(tree, prefix="", connector="", max_depth=1)
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 2
    assert out[0] == "├── a  [folder]"
    assert out[1] == "└── b  [folder]"

    capsys.readouterr()
    _render_plain_tree(tree, prefix="", connector="", max_depth=2)
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 4
    assert "confT" in out[1]
    assert out[2] == "└── b  [folder]"
    assert out[3] == "    └── c  [folder]"


def test_tree_help_excludes_ls_only_flags() -> None:
    from click.testing import CliRunner

    from ocmo_cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["tree", "--help"])
    assert result.exit_code == 0, result.output
    assert "--depth" in result.output
    assert "--recursive" not in result.output
    assert "--limit" not in result.output
    assert "--hide-folders" not in result.output
    assert "--sort" not in result.output
    assert "--hide-system" in result.output
    assert "--emoji" in result.output
    assert "--output" not in result.output


def test_tree_node_label_emoji_places_icon_before_name() -> None:
    assert (
        _tree_node_label(
            {"name": "my.conf", "node_type": "config"},
            use_emoji=True,
        )
        == "📄 my.conf"
    )
    assert (
        _tree_node_label(
            {"name": "my.secret", "node_type": "secret"},
            use_emoji=True,
        )
        == "🔒 my.secret"
    )
    assert (
        _tree_node_label(
            {"name": "my.conf", "node_type": "config"},
            use_emoji=False,
        )
        == "my.conf  [config]"
    )


def test_render_plain_tree_emoji_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _build_tree_hierarchy(
        [
            {"path": "a", "name": "a", "node_type": "folder"},
            {"path": "a/confT", "name": "confT", "node_type": "config"},
        ]
    )
    _render_plain_tree(tree, prefix="", connector="", use_emoji=True)
    out = capsys.readouterr().out
    assert "📁 a" in out
    assert "📄 confT" in out
    assert "[config]" not in out
    assert "[folder]" not in out


def test_tree_rejects_global_output_flag() -> None:
    from click.testing import CliRunner

    from ocmo_cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["-o", "json", "tree", "-n", "prod"])
    assert result.exit_code != 0
    assert "does not support -o/--output" in result.output


def test_sort_wide_rows_by_type():
    rows = [
        {"type": "config", "path": "b/cfg"},
        {"type": "folder", "path": "a"},
        {"type": "config", "path": "a/cfg"},
    ]
    sort_wide_rows(rows, "type")
    assert [row["path"] for row in rows] == ["a/cfg", "b/cfg", "a"]


def test_sort_wide_rows_by_updated():
    import datetime

    rows = [
        {"path": "old", "_updated_at": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)},
        {"path": "new", "_updated_at": datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)},
        {"path": "none", "_updated_at": None},
    ]
    sort_wide_rows(rows, "updated")
    assert [row["path"] for row in rows] == ["new", "old", "none"]


def test_sort_wide_rows_by_created():
    import datetime

    rows = [
        {"path": "old", "_created_at": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)},
        {"path": "new", "_created_at": datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)},
        {"path": "none", "_created_at": None},
    ]
    sort_wide_rows(rows, "created")
    assert [row["path"] for row in rows] == ["new", "old", "none"]


def test_render_wide_table_sorts_by_updated(capsys: pytest.CaptureFixture[str]) -> None:
    from ocmo_cli.commands.ls import _render_wide_table

    client = MagicMock()
    view = MagicMock()
    view.list_item_versions.side_effect = [
        SimpleNamespace(
            to_dict=lambda: {
                "versions_count": 1,
                "versions": [{"updater": "a", "updated_at": "2026-01-01T00:00:00+00:00"}],
            },
        ),
        SimpleNamespace(
            to_dict=lambda: {
                "versions_count": 1,
                "versions": [{"updater": "b", "updated_at": "2026-08-01T00:00:00+00:00"}],
            },
        ),
    ]
    client.can_i.return_value = SimpleNamespace(to_dict=lambda: {"allowed": {}})

    _render_wide_table(
        client,
        view,
        "prod",
        [
            {"path": "z/cfg", "node_type": "config"},
            {"path": "a/cfg", "node_type": "config"},
        ],
        sort_by="updated",
        command_name="ls",
    )
    out = capsys.readouterr().out.splitlines()
    assert "a/cfg" in out[1]
    assert "z/cfg" in out[2]


def test_navigation_rows_leaf_returns_item():
    data = {
        "item": {"name": "new.conf", "path": "audit-test/new.conf", "node_type": "config"},
        "children": [],
        "children_count": 0,
        "breadcrumbs": ["audit-test"],
        "is_leaf": True,
    }
    rows = _navigation_rows(data)
    assert rows == [data["item"]]


def test_navigation_rows_folder_returns_children():
    child = {"name": "new.conf", "path": "audit-test/new.conf", "node_type": "config"}
    data = {
        "item": {"name": "audit-test", "path": "audit-test", "node_type": "folder"},
        "children": [child],
        "children_count": 1,
        "breadcrumbs": [],
        "is_leaf": False,
    }
    assert _navigation_rows(data) == [child]


def test_navigation_rows_empty_folder_returns_empty_list():
    data = {
        "item": {"name": "empty", "path": "empty", "node_type": "folder"},
        "children": [],
        "children_count": 0,
        "breadcrumbs": [],
        "is_leaf": False,
    }
    assert _navigation_rows(data) == []


def test_basic_ls_row_omits_name():
    assert basic_ls_row(
        {
            "name": "new.conf",
            "path": "audit-test/new.conf",
            "node_type": "config",
        }
    ) == {
        "path": "audit-test/new.conf",
        "type": "config",
    }


def test_probe_operations_for_config():
    ops = probe_operations_for_node("config")
    assert "config:read" in ops
    assert "config:resolve" in ops
    assert "config:audit" in ops


def test_format_permission_string_example():
    allowed = {
        "config:write": True,
        "config:resolve": True,
        "config:tag": True,
        "config:describe": True,
    }
    assert format_permission_string("config", allowed) == "-w-xtD-"


def test_format_permission_string_folder():
    assert (
        format_permission_string(
            "folder",
            {"folder:describe": True, "folder:audit": True},
        )
        == "r--?-Da"
    )
    assert format_permission_string("folder", {"folder:describe": True}) == "r--?-D-"
    assert format_permission_string("folder", {}) == "r--?---"


def test_format_permission_string_unknown_type_is_all_dashes():
    assert format_permission_string("unknown", {}) == "-------"


def test_enrich_ls_rows_config(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    client.can_i.return_value = SimpleNamespace(
        to_dict=lambda: {
            "allowed": {
                "config:read": True,
                "config:write": True,
                "config:delete": False,
                "config:resolve": True,
                "config:tag": True,
                "config:describe": True,
                "config:audit": False,
            },
        },
    )
    view = MagicMock()
    view.list_item_versions.return_value = SimpleNamespace(
        to_dict=lambda: {
            "versions_count": 1,
            "versions": [
                {
                    "updater": "writer@example.com",
                    "updated_at": "2026-08-20T10:15:30+00:00",
                }
            ],
        },
    )

    rows = enrich_ls_rows(
        client=client,
        view=view,
        namespace="prod",
        nodes=[{"path": "audit-test/new.conf", "node_type": "config"}],
    )

    assert rows[0]["permissions"] == "rw-xtD-"
    assert rows[0]["versions"] == "1"
    assert rows[0]["author"] == "writer@example.com"
    assert rows[0]["created"]
    assert rows[0]["updated"]
    assert ":15:30" in rows[0]["updated"]
    assert rows[0]["type"] == "config"
    assert rows[0]["path"] == "audit-test/new.conf"
    client.can_i.assert_called_once()
    view.list_item_versions.assert_called_once_with(path="audit-test/new.conf", limit=1)


def test_enrich_ls_rows_config_uses_first_version_for_created():
    client = MagicMock()
    client.can_i.return_value = SimpleNamespace(to_dict=lambda: {"allowed": {}})
    view = MagicMock()
    view.list_item_versions.side_effect = [
        SimpleNamespace(
            to_dict=lambda: {
                "versions_count": 3,
                "versions": [
                    {
                        "updater": "writer@example.com",
                        "updated_at": "2026-08-20T10:15:30+00:00",
                    }
                ],
            },
        ),
        SimpleNamespace(
            to_dict=lambda: {
                "versions_count": 3,
                "versions": [
                    {
                        "updater": "creator@example.com",
                        "updated_at": "2026-01-01T08:00:00+00:00",
                    }
                ],
            },
        ),
    ]

    rows = enrich_ls_rows(
        client=client,
        view=view,
        namespace="prod",
        nodes=[{"path": "audit-test/new.conf", "node_type": "config"}],
    )

    assert rows[0]["created"]
    assert rows[0]["updated"]
    assert ":15:30" in rows[0]["updated"]
    assert rows[0]["author"] == "creator@example.com"
    assert view.list_item_versions.call_args_list == [
        ((), {"path": "audit-test/new.conf", "limit": 1}),
        ((), {"path": "audit-test/new.conf", "limit": 1, "offset": 2}),
    ]


def test_render_table_sorts_by_path(capsys: pytest.CaptureFixture[str]) -> None:
    from ocmo_cli.commands.ls import _render_table

    _render_table(
        [
            {"path": "z/item", "node_type": "config"},
            {"path": "a/item", "node_type": "folder"},
        ],
        command_name="ls",
    )
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("TYPE")
    assert out[0].index("TYPE") < out[0].index("PATH")
    assert out[1].startswith("folder")
    assert out[2].startswith("config")
    assert "a/item" in out[1]
    assert "z/item" in out[2]


def test_enrich_ls_rows_resolver_uses_get_item():
    client = MagicMock()
    client.can_i.return_value = SimpleNamespace(
        to_dict=lambda: {"allowed": {"resolver:read": True, "resolver:audit": True}},
    )
    view = MagicMock()
    view.get_item.return_value = SimpleNamespace(
        to_dict=lambda: {
            "author": "writer@example.com",
            "created_at": "2026-01-15T08:30:00+00:00",
        },
    )

    rows = enrich_ls_rows(
        client=client,
        view=view,
        namespace="prod",
        nodes=[{"path": "app/svc", "node_type": "resolver"}],
    )

    assert rows[0]["permissions"] == "r-----a"
    assert rows[0]["versions"] == "-"
    assert rows[0]["author"] == "writer@example.com"
    assert rows[0]["created"]
    assert ":30:00" in rows[0]["created"]
    assert rows[0]["updated"] == "-"
    view.get_item.assert_called_once_with(path="app/svc")
    view.list_item_versions.assert_not_called()


def test_enrich_ls_rows_folder_uses_get_item_metadata():
    client = MagicMock()
    client.can_i.return_value = SimpleNamespace(
        to_dict=lambda: {"allowed": {"folder:describe": True}},
    )
    view = MagicMock()
    view.get_item.return_value = SimpleNamespace(
        to_dict=lambda: {
            "author": "writer@example.com",
            "created_at": "2026-02-01T12:00:00+00:00",
        },
    )

    rows = enrich_ls_rows(
        client=client,
        view=view,
        namespace="prod",
        nodes=[{"path": "audit-test", "node_type": "folder"}],
    )

    assert rows[0]["permissions"] == "r--?-D-"
    assert rows[0]["versions"] == "-"
    assert rows[0]["author"] == "writer@example.com"
    assert rows[0]["created"]
    assert ":00:00" in rows[0]["created"]
    assert rows[0]["updated"] == "-"
    view.get_item.assert_called_once_with(path="audit-test")
    view.list_item_versions.assert_not_called()


def test_enrich_ls_rows_folder_skips_version_probe():
    client = MagicMock()
    client.can_i.return_value = SimpleNamespace(
        to_dict=lambda: {"allowed": {"folder:describe": True}},
    )
    view = MagicMock()
    view.get_item.side_effect = Exception("forbidden")

    rows = enrich_ls_rows(
        client=client,
        view=view,
        namespace="prod",
        nodes=[{"path": "audit-test", "node_type": "folder"}],
    )

    assert rows[0]["permissions"] == "r--?-D-"
    assert rows[0]["versions"] == "-"
    assert rows[0]["author"] == "-"
    assert rows[0]["created"] == "-"
    assert rows[0]["updated"] == "-"
    view.list_item_versions.assert_not_called()
