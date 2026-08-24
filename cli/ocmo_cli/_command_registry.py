"""Startup-safe short help for hand-written CLI commands."""

from __future__ import annotations

HAND_WRITTEN_SHORT_HELP: dict[str, tuple[str, str, str]] = {
    "auth": ("auth", "auth_group", "Authenticate with the OCMO server."),
    "config": ("config_cmd", "config_group", "Manage local CLI configuration (server, contexts, auth)."),
    "describe": ("describe", "describe_cmd", "Read or set the Markdown description of a tree item."),
    "resolve": ("resolve", "resolve_group", "Resolve a config or folder to its final value(s)."),
    "export": ("export", "export_cmd", "Export a subtree to disk, preserving tree structure."),
    "import": ("import_", "import_cmd", "Import a directory tree into OCMO."),
    "apply": ("apply", "apply_cmd", "Create or update a tree item from a local file."),
    "edit": ("edit", "edit_group", "Open a tree item in $EDITOR and update it on save."),
    "ls": ("ls", "ls_cmd", "List the direct children of a tree path, or the namespace root when ADDRESS is omitted."),
    "tree": ("ls", "tree_cmd", "Render the subtree under a path in tree format."),
    "diff": ("diff", "diff_cmd", "Show a unified diff between two versions or two items."),
    "schema": ("schema", "schema_cmd", "Render the JSON Schema for a resource type."),
    "version": ("version_cmd", "version_cmd", "Print CLI, SDK, and server versions with a compatibility verdict."),
    "whoami": ("whoami", "whoami_cmd", "Show the identity of the current authenticated principal."),
    "can-i": ("can_i", "can_i_cmd", "Check whether the current principal may perform one or more operations."),
    "api-health": (
        "api_health",
        "api_health_cmd",
        "Check API dependency health (database, cache, and related backends).",
    ),
    "completion": ("completion", "completion_cmd", "Emit a shell completion script."),
    "timeline": ("timeline", "timeline_group", "Item-scoped audit timelines."),
    "resolve-series": ("resolve_series", "resolve_series_group", "Resolve statistics over time."),
}
