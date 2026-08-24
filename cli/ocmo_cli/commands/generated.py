"""Generated command groups built from commands.yaml at import time.

For each unique action in commands.yaml that is NOT hand-written, a Click Group
is created (e.g. `get`, `create`, `delete`, ...). Within each group, a subcommand
is created for each resource type (e.g. `get config`, `get namespace`, ...).

Since commands.yaml is a committed file, this is equivalent to code generation
in terms of determinism and startup behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

import click

from .._body_payload import (
    BODY_PAYLOADS,
    format_usage_error,
    prepare_body_payload,
    prepare_untag_body_payload,
    sdk_path_for_body_payload,
    validate_create_request,
    validate_tag_request,
)
from .._click_groups import ResourceAliasGroup
from .._client import OcmoCtx
from .._item_output import (
    emit_item_result,
    item_output_format,
    item_output_includes_token_in_payload,
    uses_item_output,
)
from .._options import (
    get_cast_output_option,
    get_item_output_option,
    namespace_option,
    output_option,
    tree_version_option,
)
from .._output_manifest import (
    command_key as output_command_key,
)
from .._output_manifest import (
    emit_command_output,
    get_command_spec,
    resolve_effective_format,
)
from .._sdk_dispatch import (
    NO_ADDRESS_OPS as _NO_ADDRESS_OPS,
)
from .._sdk_dispatch import (
    NON_TREE_ADDRESS_OPS as _NON_TREE_ADDRESS_OPS,
)
from .._sdk_dispatch import (
    VERSION_ADDRESS_OPS as _VERSION_ADDRESS_OPS,
)
from .._sdk_dispatch import (
    VERSION_FILTER_OPS as _VERSION_FILTER_OPS,
)
from .._sdk_dispatch import (
    address_optional_for_command,
    address_required_for_op,
    build_sdk_call,
    extra_params_for_ops,
    pick_op_id,
)


def _op_scope(op_id: str, ops_meta: dict[str, Any]) -> str:
    return str(ops_meta.get(op_id, {}).get("scope", "namespace"))


def _command_is_client_scoped(op_ids: list[str], ops_meta: dict[str, Any]) -> bool:
    """True when every mapped operation for this command is client-scoped."""
    if not op_ids:
        return False
    return all(_op_scope(op_id, ops_meta) == "client" for op_id in op_ids)


def _reject_namespace_if_client_scoped(
    *,
    op_ids: list[str],
    ops_meta: dict[str, Any],
    namespace_explicit: bool,
) -> None:
    from .._exit import USAGE_ERROR  # deferred

    if not _command_is_client_scoped(op_ids, ops_meta):
        return
    if not namespace_explicit:
        return
    print(
        "Error: -n/--namespace is not valid for this command.",
        file=sys.stderr,
    )
    raise SystemExit(USAGE_ERROR)


def _namespace_explicit_on_cli(
    click_ctx: click.Context,
    *,
    use_namespace_option: bool,
) -> bool:
    """True when -n/--namespace was passed on the CLI (not from env/config alone)."""
    from click.core import ParameterSource

    if use_namespace_option:
        source = click_ctx.get_parameter_source("namespace")
        if source == ParameterSource.COMMANDLINE:
            return True
    ctx: click.Context | None = click_ctx
    while ctx is not None:
        try:
            source = ctx.get_parameter_source("namespace")
        except LookupError:
            source = None
        if source == ParameterSource.COMMANDLINE:
            return True
        ctx = ctx.parent
    return False


from .._generated_registry import action_help as _action_help  # noqa: E402

_RESOURCE_HELP: dict[str, str] = {
    "namespace": "Namespace metadata.",
    "item": "A tree item (config, template, secret, resolver, or folder). "
    "Address may include @version or @tag (e.g. app/web@2, app/web@stable).",
    "config": "A configuration item.",
    "template": "A template item.",
    "secret": "A secret item.",
    "resolver": "A resolver item.",
    "folder": "A folder in the tree.",
    "version": "Version history for an item.",
    "lock": "An active edit lock.",
    "audit": "Audit log events.",
    "globalpermission": "A global permission rule.",
    "cast": "Available resolve cast formats.",
    "tree": "Tree navigation and search results.",
    "parameters": "Dynamic resolve parameters.",
    "draft": "A resolve draft.",
    "token": "A resolver authentication token.",
}

_ACTION_RESOURCE_HELP: dict[tuple[str, str], str] = {
    ("get", "namespace"): (
        "List namespaces or show one. ADDRESS is the namespace name (omit to list all). "
        "Default table shows name and description; use -o wide for all fields."
    ),
    ("create", "namespace"): ("Create a namespace. ADDRESS is the name; use --description for details."),
    ("update", "namespace"): "Update namespace metadata. ADDRESS is the namespace name.",
    ("delete", "namespace"): "Delete a namespace. ADDRESS is the namespace name.",
    ("get", "version"): (
        "List version history for a tree item. ADDRESS is the item path, optionally "
        "with @version or @tag (e.g. app/web@26, app/web@stable). Use --limit to "
        "cap results and --tagged-only to omit untagged versions."
    ),
    ("get", "item"): (
        "Show a tree item or list items in the namespace. ADDRESS is the item path "
        "with optional @version or @tag (omit to list). Use --limit to cap list "
        "results and --type to filter by item type (repeatable)."
    ),
    ("get", "cast"): (
        "List resolve cast formats or show one format's option schema. "
        "ADDRESS is the format name (e.g. yaml, json; omit to list all)."
    ),
    ("get", "audit"): (
        "List audit events or show one. ADDRESS is the event id " "(full UUID or a unique hex prefix; omit to list)."
    ),
    ("get", "lock"): "List locks or show one. ADDRESS is the tree path (omit to list all).",
    ("create", "lock"): ("Create a lock. ADDRESS is the tree path; use --reason and optionally --expires-at."),
    ("update", "lock"): ("Update a lock. ADDRESS is the tree path; use --reason and optionally --expires-at."),
    ("delete", "lock"): "Remove a lock. ADDRESS is the tree path.",
    ("get", "globalpermission"): (
        "List global permission rules or show one. "
        "ADDRESS is the rule id (user-defined id or UUID; omit to list all)."
    ),
    ("create", "globalpermission"): (
        "Create a rule. ADDRESS is optional rule id; use -f for the rule body "
        "and --position to reorder after create."
    ),
    ("update", "globalpermission"): (
        "Update a rule. ADDRESS is the rule id (user-defined id or UUID); use -f for the rule body."
    ),
    ("delete", "globalpermission"): ("Delete a rule. ADDRESS is the rule id (user-defined id or UUID)."),
    ("move", "globalpermission"): (
        "Reorder a rule. ADDRESS is the rule id (user-defined id or UUID); "
        "use --position to set the new sort position."
    ),
    ("rotate", "token"): (
        "Rotate a resolver access token. ADDRESS is the resolver path; "
        "--token-number selects which token slot to rotate."
    ),
}


def _resource_command_help(action: str, resource: str) -> str:
    return _ACTION_RESOURCE_HELP.get(
        (action, resource),
        _RESOURCE_HELP.get(resource, f"{action.capitalize()} {resource}."),
    )


# Resource type aliases (canonical → set of aliases)
from .._resource_aliases import RESOURCE_ALIASES  # noqa: E402


def _load_commands_yaml() -> dict[str, Any]:
    from ocmo_cli._commands_map import OPERATIONS  # static Python dict, no YAML at startup

    return OPERATIONS


def _entries_for_action(action: str) -> list[tuple[str, str, dict[str, Any]]]:
    operations = _load_commands_yaml()
    if action == "untag":
        set_tag_cfg = operations.get("set_tag")
        if isinstance(set_tag_cfg, dict) and not set_tag_cfg.get("hand_written") and not set_tag_cfg.get("skip"):
            return [("set_tag", "item", dict(set_tag_cfg))]
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for op_id, config in operations.items():
        if not isinstance(config, dict):
            continue
        if config.get("hand_written") or config.get("skip"):
            continue
        entry_action = config.get("action")
        resource = config.get("resource")
        if entry_action != action or not resource:
            continue
        # Hand-written ``resolve`` command owns config resolve; only draft/parameters are generated.
        if entry_action == "resolve":
            continue
        entries.append((op_id, resource, config))
    return entries


def build_action_group(action: str) -> click.Group:
    """Build one generated Click command group."""
    entries = _entries_for_action(action)
    if not entries:
        raise ValueError(f"no generated operations for action {action!r}")
    return _build_action_group(action, entries)


def build_generated_groups() -> list[click.Group]:
    """Build and return all generated Click command groups."""
    from .._generated_registry import generated_action_names

    return [build_action_group(action) for action in generated_action_names()]


def build_resolve_subcommands() -> list[click.Command]:
    """Subcommands merged into the hand-written ``resolve`` group."""
    operations = _load_commands_yaml()
    by_resource: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for op_id, config in operations.items():
        if not isinstance(config, dict) or config.get("hand_written") or config.get("skip"):
            continue
        if config.get("action") != "resolve":
            continue
        resource = config.get("resource")
        if not resource:
            continue
        by_resource.setdefault(resource, []).append((op_id, config))

    commands: list[click.Command] = []
    for resource, resource_entries in sorted(by_resource.items()):
        op_ids = [op_id for op_id, _ in resource_entries]
        config = resource_entries[0][1]
        commands.append(_build_resource_command("resolve", resource, op_ids, config))
    return commands


def _build_action_group(action: str, entries: list[tuple[str, str, dict[str, Any]]]) -> click.Group:
    """Build a Click Group for an action (e.g. 'get', 'create', 'delete')."""

    group_help = _action_help(action)

    @click.group(action, cls=ResourceAliasGroup, help=group_help)
    @click.pass_context
    def action_group(ctx: click.Context) -> None:
        pass

    # Group operations by resource (multiple op_ids may share action+resource).
    by_resource: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for op_id, resource, config in entries:
        by_resource.setdefault(resource, []).append((op_id, config))

    for resource, resource_entries in sorted(by_resource.items()):
        op_ids = [op_id for op_id, _ in resource_entries]
        config = resource_entries[0][1]
        cmd = _build_resource_command(action, resource, op_ids, config)
        action_group.add_resource_command(
            cmd,
            canonical=resource,
            aliases=RESOURCE_ALIASES.get(resource, []),
        )

    return action_group


def _build_resource_command(action: str, resource: str, op_ids: list[str], config: dict[str, Any]) -> click.Command:
    """Build a Click Command for action+resource, wired to the SDK method."""

    confirm_mode = config.get("confirm")

    is_rotate_token = action == "rotate" and resource == "token"
    is_mutating = action in ("create", "update", "delete", "move", "copy", "tag", "untag", "rotate", "propagate")

    resource_help = _resource_command_help(action, resource)
    extra_specs = extra_params_for_ops(op_ids)
    supports_version_address = any(op_id in _VERSION_ADDRESS_OPS for op_id in op_ids) or any(
        op_id in _VERSION_FILTER_OPS for op_id in op_ids
    )
    supports_file_body = (
        action not in ("tag", "untag", "delete", "propagate", "move", "copy")
        and not is_rotate_token
        and not (action == "create" and resource in ("namespace", "lock"))
        and not (action == "update" and resource == "lock")
    )
    output_key = output_command_key(action, resource)
    address_required = not address_optional_for_command(
        op_ids,
        action=action,
        resource=resource,
    )
    get_item_list_mode = action == "get" and resource == "item"
    get_cast_dual_mode = action == "get" and resource == "cast"
    ops_meta = _load_ops_yaml()
    use_namespace_option = not _command_is_client_scoped(op_ids, ops_meta)

    @click.pass_context
    def resource_cmd(
        click_ctx: click.Context,
        /,
        address: str | None,
        output_fmt: str | None = None,
        field: str | None = None,
        version_flag: str | None = None,
        list_limit: int | None = None,
        item_types: tuple[str, ...] = (),
        dry_run: bool = False,
        yes: bool = False,
        file_path: str | None = None,
        _op_ids: list[str] = op_ids,
        _action: str = action,
        _resource: str = resource,
        _confirm_mode: str | None = confirm_mode,
        _extra_specs: list[Any] = extra_specs,
        **_ignored: Any,
    ) -> None:
        ocmo_ctx = click_ctx.obj
        namespace = click_ctx.params.get("namespace")
        namespace_explicit = _namespace_explicit_on_cli(
            click_ctx,
            use_namespace_option=use_namespace_option,
        )
        sdk_extra = {
            spec.sdk_name: click_ctx.params.get(spec.sdk_name)
            for spec in _extra_specs
            if click_ctx.params.get(spec.sdk_name) is not None
        }
        if _action == "get" and _resource == "item":
            if list_limit is not None:
                sdk_extra["limit"] = list_limit
        _execute_generated(
            ctx=ocmo_ctx,
            op_ids=_op_ids,
            action=_action,
            resource=_resource,
            address=address,
            namespace=namespace,
            output_fmt=output_fmt,
            field=field,
            version_flag=version_flag,
            dry_run=dry_run or (ocmo_ctx and ocmo_ctx.dry_run),
            yes=yes or (ocmo_ctx and ocmo_ctx.yes),
            file_path=file_path,
            confirm_mode=_confirm_mode,
            sdk_extra=sdk_extra,
            namespace_explicit=namespace_explicit,
            item_types=item_types,
        )

    # Apply Click decorators inside-out: options/arguments first, command last.
    for spec in reversed(extra_specs):
        opt_name = f"--{spec.click_name}"
        if spec.is_flag:
            resource_cmd = click.option(
                opt_name,
                spec.sdk_name,
                is_flag=True,
                default=False,
                help=spec.help,
            )(resource_cmd)
        elif spec.type_ is int:
            token_required = is_rotate_token and spec.sdk_name == "token_number"
            resource_cmd = click.option(
                opt_name,
                spec.sdk_name,
                type=int,
                required=token_required,
                default=None,
                help=spec.help,
            )(resource_cmd)
        elif spec.type_ is float:
            resource_cmd = click.option(
                opt_name,
                spec.sdk_name,
                type=float,
                default=None,
                help=spec.help,
            )(resource_cmd)
        else:
            tag_required = action in ("tag", "untag") and spec.sdk_name == "tag"
            if tag_required:
                resource_cmd = click.option(
                    opt_name,
                    spec.sdk_name,
                    required=True,
                    help=spec.help,
                )(resource_cmd)
            else:
                resource_cmd = click.option(
                    opt_name,
                    spec.sdk_name,
                    default=None,
                    help=spec.help,
                )(resource_cmd)
    if not is_rotate_token:
        resource_cmd = click.option(
            "--field",
            default=None,
            metavar="PATH",
            help="Extract a specific dot-path field from the response (e.g. version_data.data).",
        )(resource_cmd)
    if is_mutating:
        if supports_file_body:
            resource_cmd = click.option(
                "-f", "--file", "file_path", default=None, help="YAML/JSON body from file ('-' for stdin)."
            )(resource_cmd)
        if confirm_mode == "destructive":
            resource_cmd = click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompts.")(
                resource_cmd
            )
        resource_cmd = click.option("--dry-run", is_flag=True, default=False, help="Print plan without sending.")(
            resource_cmd
        )
    if get_item_list_mode:
        from .._get_item_list import GET_ITEM_TYPE_CHOICES

        resource_cmd = click.option(
            "--limit",
            "list_limit",
            type=int,
            default=None,
            help="Maximum number of items to return.",
        )(resource_cmd)
        resource_cmd = click.option(
            "--type",
            "item_types",
            multiple=True,
            type=click.Choice(GET_ITEM_TYPE_CHOICES, case_sensitive=False),
            help=("Filter by item type (repeatable). " "Default: config, template, secret, resolver."),
        )(resource_cmd)
        resource_cmd = get_item_output_option()(resource_cmd)
    elif get_cast_dual_mode:
        resource_cmd = get_cast_output_option()(resource_cmd)
    elif not is_rotate_token:
        resource_cmd = output_option(output_key)(resource_cmd)
    if supports_version_address:
        resource_cmd = tree_version_option()(resource_cmd)
    if use_namespace_option:
        resource_cmd = namespace_option()(resource_cmd)
    resource_cmd = click.argument("address", required=address_required)(resource_cmd)
    return click.command(resource, help=resource_help)(resource_cmd)


def _execute_generated(
    *,
    ctx: OcmoCtx,
    op_ids: list[str],
    action: str,
    resource: str,
    address: str | None,
    namespace: str | None,
    output_fmt: str | None,
    field: str | None = None,
    version_flag: str | None = None,
    dry_run: bool,
    yes: bool,
    file_path: str | None,
    confirm_mode: str | None,
    sdk_extra: dict[str, Any] | None = None,
    namespace_explicit: bool = False,
    item_types: tuple[str, ...] = (),
) -> None:
    from .._address import AddressError, parse_address, parse_simple_address  # deferred
    from .._errors import handle_sdk_error  # deferred
    from .._exit import USAGE_ERROR  # deferred
    from .._output import as_dict, extract_field, sanitize_for_output, status  # deferred  # deferred
    from .._output import confirm as _confirm
    from .._resolver_output import print_resolver_token  # deferred

    list_mode = action == "get" and resource == "item" and not address
    cast_list_mode = action == "get" and resource == "cast" and not address
    cast_show_mode = action == "get" and resource == "cast" and bool(address)
    cast_format: str | None = None

    try:
        ops_meta = _load_ops_yaml()
        _reject_namespace_if_client_scoped(
            op_ids=op_ids,
            ops_meta=ops_meta,
            namespace_explicit=namespace_explicit,
        )
        if list_mode:
            op_id = "search_root"
        elif cast_list_mode or cast_show_mode:
            op_id = "list_cast_formats"
        else:
            op_id = pick_op_id(op_ids, address=address, namespace=namespace, ops_meta=ops_meta)

        path: str | None = None
        version: str | None = None
        audit_show_mode = action == "get" and resource == "audit" and bool(address)
        if address and not (cast_list_mode or cast_show_mode or audit_show_mode):
            parser = parse_simple_address if op_id in _NON_TREE_ADDRESS_OPS else parse_address
            try:
                path, version = parser(address, version_flag=version_flag)
            except AddressError as e:
                print(f"Error: {e}", file=sys.stderr)
                raise SystemExit(USAGE_ERROR)
        elif cast_show_mode:
            assert address is not None
            try:
                cast_format, version = parse_simple_address(
                    address,
                    version_flag=version_flag,
                )
            except AddressError as e:
                print(f"Error: {e}", file=sys.stderr)
                raise SystemExit(USAGE_ERROR)
            if version:
                print(
                    "Error: cast format ADDRESS does not support @version or --version.",
                    file=sys.stderr,
                )
                raise SystemExit(USAGE_ERROR)
        elif audit_show_mode:
            assert address is not None
            try:
                path, version = parse_simple_address(
                    address,
                    version_flag=version_flag,
                )
            except AddressError as e:
                print(f"Error: {e}", file=sys.stderr)
                raise SystemExit(USAGE_ERROR)
            if version:
                print(
                    "Error: audit event ADDRESS does not support @version or --version.",
                    file=sys.stderr,
                )
                raise SystemExit(USAGE_ERROR)

        # Some operations use query-only parameters and ignore tree addresses.
        if op_id in _NO_ADDRESS_OPS:
            path = None
            version = None

        if path is None and address_required_for_op(
            op_id,
            action=action,
            resource=resource,
        ):
            print(
                f"Error: ADDRESS is required for ocmo {action} {resource}.",
                file=sys.stderr,
            )
            raise SystemExit(USAGE_ERROR)

        merged_extra = dict(sdk_extra or {})
        if list_mode:
            from .._get_item_list import prepare_get_item_list_extra  # deferred

            merged_extra = prepare_get_item_list_extra(merged_extra, item_types=item_types)
        if op_id == "list_item_versions":
            from .._version_output import apply_version_address_query  # deferred

            apply_version_address_query(merged_extra, version)
            version = None
        gp_create_position: float | None = None
        if op_id == "create_global_permission":
            raw_position = merged_extra.pop("position", None)
            if raw_position is not None:
                gp_create_position = float(raw_position)
        content: str | None = None
        if file_path:
            content = sys.stdin.read() if file_path == "-" else Path(file_path).read_text()

        body_payload: dict[str, Any] | None = None
        untag_mode = action == "untag" and op_id == "set_tag"
        if untag_mode:
            tag_name = merged_extra.pop("tag", None)
            validate_tag_request("set_tag", action="untag", extra={"tag": tag_name})
            body_payload = prepare_untag_body_payload(str(tag_name))
            merged_extra = {}
        elif op_id in BODY_PAYLOADS:
            try:
                body_payload = prepare_body_payload(
                    op_id,
                    address=path,
                    content=content,
                    extra=merged_extra,
                    address_version=version,
                )
            except ValueError as exc:
                print(f"Error: {format_usage_error(exc)}", file=sys.stderr)
                raise SystemExit(USAGE_ERROR)
            if action == "create" or op_id == "replace_lock":
                validate_create_request(op_id, address=path, payload=body_payload)
            content = None
            merged_extra = {}

        if op_id == "set_tag":
            validate_tag_request(op_id, payload=body_payload, extra=merged_extra)

        delete_preview = False
        if op_id == "delete_item":
            delete_preview = bool(merged_extra.pop("preview", False))

        if dry_run:
            args, kwargs = build_sdk_call(
                op_id,
                path=sdk_path_for_body_payload(op_id, path, body_payload),
                version=version,
                content=content,
                extra=merged_extra,
            )
            if body_payload is not None:
                kwargs["body"] = body_payload
            from .._dry_run import emit_dry_run_plan, format_generated_dry_run  # deferred

            display_ns = namespace if isinstance(namespace, str) and namespace else None
            if display_ns is None and ctx is not None:
                ctx_ns = getattr(ctx, "namespace", None)
                if isinstance(ctx_ns, str) and ctx_ns:
                    display_ns = ctx_ns
            client_scope = ops_meta.get(op_id, {}).get("scope") == "client"
            emit_dry_run_plan(
                format_generated_dry_run(
                    op_id=op_id,
                    action=action,
                    resource=resource,
                    path=path,
                    version=version,
                    namespace=display_ns,
                    args=args,
                    kwargs=kwargs,
                    client_scope=client_scope,
                    file_path=file_path,
                    gp_create_position=gp_create_position,
                    cast_format=cast_format,
                )
            )
            return

        if confirm_mode == "destructive" and not yes and not delete_preview:
            confirm_message = _destructive_confirm_message(
                op_id=op_id,
                action=action,
                resource=resource,
                path=path,
                version=version,
            )
            if not _confirm(confirm_message, yes=False):
                status("Aborted.")
                raise SystemExit(0)

        args, kwargs = build_sdk_call(
            op_id,
            path=sdk_path_for_body_payload(op_id, path, body_payload),
            version=version,
            content=content,
            extra=merged_extra,
        )
        if op_id == "delete_item":
            kwargs["preview"] = delete_preview
        if body_payload is not None:
            kwargs["body"] = body_payload
        result = _call_sdk_method(ctx, op_id, namespace, args, kwargs)

        if op_id == "set_tag" and path is not None:
            from .._version_output import emit_item_versions_output

            ns_view = ctx.namespace_view(namespace)
            emit_item_versions_output(
                ns_view,
                path,
                version=version,
                output_fmt=output_fmt,
                ctx_fmt=ctx.output if ctx else None,
                field=field,
            )
            return

        if op_id == "delete_item" and result is not None:
            from .._delete_item_output import emit_delete_item_output

            if field:
                data = sanitize_for_output(as_dict(result, fallback_vars=False) or result)
                extract_field(data, field)
            else:
                emit_delete_item_output(
                    result,
                    target_path=path,
                    version=version,
                    output_fmt=output_fmt,
                    ctx_fmt=ctx.output if ctx else None,
                )
            return

        if op_id == "rotate_resolver_token":
            if result is None or not print_resolver_token(result):
                print(
                    "Error: resolver token was not returned by the API.",
                    file=sys.stderr,
                )
                raise SystemExit(USAGE_ERROR)
            return

        if op_id == "create_global_permission" and gp_create_position is not None and result is not None:
            rule_id = _created_resource_label(result)
            current_position = getattr(result, "position", None)
            if current_position != gp_create_position and rule_id is not None:
                result = _call_sdk_method(
                    ctx,
                    "move_global_permission",
                    namespace,
                    [rule_id],
                    {"body": {"position": gp_create_position}},
                )

        if action in ("create", "update"):
            label = path or _created_resource_label(result)
            if label:
                verb = "Created" if action == "create" else "Updated"
                status(f"{verb} {resource} {label!r}.")

        output_key = (
            "get item list"
            if list_mode
            else "get cast list"
            if cast_list_mode
            else output_command_key(action, resource)
        )

        if result is not None and (cast_list_mode or cast_show_mode):
            from .._get_cast_output import CastFormatNotFoundError, cast_list_rows, cast_show_payload

            if cast_list_mode:
                data = cast_list_rows(as_dict(result, fallback_vars=False) or result)
            else:
                try:
                    data = cast_show_payload(
                        as_dict(result, fallback_vars=False) or result,
                        cast_format or "",
                    )
                except CastFormatNotFoundError as exc:
                    print(f"Error: {exc}", file=sys.stderr)
                    raise SystemExit(USAGE_ERROR) from exc
            if field:
                extract_field(data, field)
            else:
                emit_command_output(
                    output_key,
                    data,
                    output_fmt,
                    ctx_fmt=ctx.output if ctx else None,
                )
            return

        if result is not None and uses_item_output(op_id, action, resource, result):
            fmt = item_output_format(
                output_fmt,
                ctx.output if ctx else None,
                command_key=output_key,
            )
            if field:
                data = sanitize_for_output(as_dict(result, fallback_vars=False) or result)
                extract_field(data, field)
            else:
                emit_item_result(
                    result,
                    fmt,
                    no_color=bool(ctx and ctx.no_color),
                    resource=resource,
                )
                if op_id == "create_resolver" and not item_output_includes_token_in_payload(fmt, field):
                    print_resolver_token(result)
            return

        if result is not None:
            if isinstance(result, list):
                data = [sanitize_for_output(as_dict(r)) for r in result]
            else:
                data = sanitize_for_output(as_dict(result, fallback_vars=False) or result)

            if field:
                extract_field(data, field)
            else:
                emit_command_output(
                    output_key,
                    data,
                    output_fmt,
                    ctx_fmt=ctx.output if ctx else None,
                )
                if op_id == "create_resolver" and not _structured_output_includes_token(
                    resolve_effective_format(
                        output_fmt,
                        ctx.output if ctx else None,
                        get_command_spec(output_key),
                    ),
                    field,
                ):
                    print_resolver_token(result)

    except KeyboardInterrupt:
        raise SystemExit(130)
    except SystemExit:
        raise
    except Exception as exc:
        handle_sdk_error(exc)


def _destructive_confirm_message(
    *,
    op_id: str,
    action: str,
    resource: str,
    path: str | None,
    version: str | None,
) -> str:
    if op_id == "delete_item" and version:
        return f"This will delete version {version} for item {path!r}. Continue?"
    return f"This will {action} {resource} {path!r}. Continue?"


def _created_resource_label(result: Any) -> str | None:
    for key in ("name", "path", "id"):
        value = getattr(result, key, None)
        if value is not None and value != "":
            return str(value)
    return None


def _call_sdk_method(
    ctx: OcmoCtx,
    op_id: str,
    namespace: str | None,
    args: list[Any],
    kwargs: dict[str, Any],
) -> Any:
    """Dispatch to the correct SDK method based on operation scope."""
    ops_yaml = _load_ops_yaml()
    scope = ops_yaml.get(op_id, {}).get("scope", "namespace")

    if scope == "client":
        client = ctx.client()
        method = getattr(client, op_id, None)
        if method is None:
            print(f"Error: SDK method {op_id!r} not found on client.", file=sys.stderr)
            raise SystemExit(1)
        return method(*args, **kwargs)

    view = ctx.namespace_view(namespace)
    method = getattr(view, op_id, None)
    if method is None:
        print(f"Error: SDK method {op_id!r} not found on namespace view.", file=sys.stderr)
        raise SystemExit(1)
    return method(*args, **kwargs)


def _structured_output_includes_token(fmt: str, field: str | None) -> bool:
    """True when stdout already carries the resolver token in structured output."""
    if field:
        return field in ("token1", "token")
    if fmt in ("yaml", "json", "table"):
        return True
    return fmt.startswith("jsonpath=token") or fmt.startswith("jsonpath=token1")


def _load_ops_yaml() -> dict[str, Any]:
    from pathlib import Path

    import yaml  # deferred

    ops_path = Path(__file__).parent.parent.parent.parent / "sdk" / "operations.yaml"
    if not ops_path.exists():
        return {}
    with ops_path.open() as f:
        data = yaml.safe_load(f) or {}
    return cast(dict[str, Any], data.get("operations", {}))
