"""ocmo edit — open an item in $EDITOR and update on save."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any

import click

from .._address import parse_address_or_exit
from .._click_groups import ResourceAliasGroup
from .._client import OcmoCtx
from .._errors import sdk_command
from .._exit import USAGE_ERROR
from .._item_output import (
    deleted_version_edit_error,
    emit_item_result,
    item_body,
    item_output_format,
    item_version_is_deleted,
    node_type_of,
)
from .._options import namespace_option, output_option, tree_version_option
from .._output import err, status
from .._resource_aliases import RESOURCE_ALIASES

if TYPE_CHECKING:
    from ocmo import NamespaceView

_EDIT_RESOURCES = ("config", "template", "secret", "resolver")

_EDIT_GROUP_HELP = """\
Open a tree item in $EDITOR and update it on save.

Fetches the current document body, opens it in $EDITOR (or $VISUAL, defaulting to vi),
then submits an update when the file changes."""


@click.group("edit", cls=ResourceAliasGroup, help=_EDIT_GROUP_HELP)
def edit_group() -> None:
    """Edit tree document items interactively."""


def _build_edit_command(resource: str) -> click.Command:
    output_key = f"edit {resource}"
    resource_help = (
        f"Edit a {resource} item. ADDRESS is the tree path, optionally with " "@version or @tag (e.g. app/web@stable)."
    )

    @click.command(resource, help=resource_help)
    @click.argument("address")
    @namespace_option()
    @output_option(output_key)
    @tree_version_option()
    @click.pass_obj
    @sdk_command
    def edit_resource_cmd(
        ctx: OcmoCtx,
        address: str,
        namespace: str | None,
        output_fmt: str | None,
        version_flag: str | None,
        *,
        _resource: str = resource,
    ) -> None:
        _run_edit(
            ctx=ctx,
            resource=_resource,
            address=address,
            namespace=namespace,
            output_fmt=output_fmt,
            version_flag=version_flag,
        )

    return edit_resource_cmd


for _resource in _EDIT_RESOURCES:
    edit_group.add_resource_command(
        _build_edit_command(_resource),
        canonical=_resource,
        aliases=RESOURCE_ALIASES.get(_resource, []),
    )


def _run_edit(
    *,
    ctx: OcmoCtx,
    resource: str,
    address: str,
    namespace: str | None,
    output_fmt: str | None,
    version_flag: str | None,
) -> None:
    path, version = parse_address_or_exit(address, version_flag=version_flag)
    ns = ctx.require_namespace(namespace)
    view = ctx.namespace_view(namespace)

    if ctx.dry_run:
        from .._dry_run import emit_dry_run_plan, format_edit_dry_run  # deferred

        emit_dry_run_plan(
            format_edit_dry_run(
                resource=resource,
                path=path,
                namespace=ns,
            )
        )
        return

    get_kwargs: dict[str, Any] = {}
    if version is not None:
        get_kwargs["version"] = version
    if resource == "secret":
        get_kwargs["reveal"] = True

    item = view.get_item(path=path, **get_kwargs)
    actual_type = node_type_of(item)
    if actual_type and actual_type != resource:
        err(f"Item {path!r} is a {actual_type}, not a {resource}.")
        raise SystemExit(USAGE_ERROR)

    if item_version_is_deleted(item):
        err(deleted_version_edit_error(path, item))
        raise SystemExit(USAGE_ERROR)

    content = item_body(item, resource=resource)
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"

    if resource == "secret":
        new_content = _edit_in_secure_temp(content, editor)
    else:
        new_content = _edit_in_temp_file(content, editor, suffix=".yaml")

    if new_content == content:
        print("No changes.")
        return

    result = _update_item(view, path, new_content, resource)
    status(f"Updated {resource} {path!r}.")

    fmt = item_output_format(
        output_fmt,
        ctx.output,
        command_key=f"edit {resource}",
    )
    emit_item_result(result, fmt, no_color=ctx.no_color, resource=resource)


def _edit_in_temp_file(content: str, editor: str, *, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as handle:
        handle.write(content)
        tmp_path = handle.name

    try:
        _run_editor(editor, tmp_path)
        with open(tmp_path, encoding="utf-8") as handle:
            return handle.read()
    finally:
        os.unlink(tmp_path)


def _edit_in_secure_temp(content: str, editor: str) -> str:
    """Edit a secret in a secure temp directory with 0700/0600 permissions."""
    tmp_dir = tempfile.mkdtemp()
    os.chmod(tmp_dir, 0o700)
    tmp_path = os.path.join(tmp_dir, "secret")

    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            os.chmod(tmp_path, 0o600)
            handle.write(content)

        _run_editor(editor, tmp_path)

        with open(tmp_path, encoding="utf-8") as handle:
            return handle.read()
    finally:
        if os.path.exists(tmp_path):
            size = os.path.getsize(tmp_path)
            with open(tmp_path, "wb") as handle:
                handle.write(b"\x00" * size)
            os.unlink(tmp_path)
        os.rmdir(tmp_dir)


def _run_editor(editor: str, path: str) -> None:
    args = shlex.split(editor) + [path]
    result = subprocess.run(args)
    if result.returncode != 0:
        err(f"Editor exited with code {result.returncode}.")
        raise SystemExit(1)


def _update_item(view: NamespaceView, path: str, content: str, resource: str) -> Any:
    method = getattr(view, f"update_{resource}")
    return method(path=path, content=content)
